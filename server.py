import argparse
import asyncio
import functools
import logging
import os
import time
from contextlib import contextmanager
from enum import Enum

import aiohttp
import anyio
import async_timeout
import pymorphy2
from aiohttp import web

import adapters
import text_tools
from adapters import SANITIZERS

logger = logging.getLogger(__file__)


class ProcessingStatus(Enum):
    OK = 'OK'
    FETCH_ERROR = 'FETCH_ERROR'
    PARSING_ERROR = 'PARSING_ERROR'
    TIMEOUT = 'TIMEOUT'


def create_args_parser():
    parser = argparse.ArgumentParser(description='Jaundice news rate server')

    parser.add_argument(
        '--max_urls',
        default=10,
        metavar='{maximum number of urls}',
        help=(
            'The maximum number of urls to analyze, 10 by default'
        ),
        type=int
    )
    return parser


@contextmanager
def check_time(url):
    start = time.monotonic()
    try:
        yield
    finally:
        end = time.monotonic()
        total = round(end - start, 2)
        logger.info(
            'The analysis of the text from %s was completed in %s seconds',
            url,
            total
        )


async def fetch(session, url, fetch_timeout):
    async with async_timeout.timeout(fetch_timeout):
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.text()


async def process_article(
    url,
    charged_words,
    articles_cards,
    morph,
    **kwargs
):
    fetch_timeout = kwargs.get('fetch_timeout', 5)
    analysis_timeout = kwargs.get('analysis_timeout', 3)
    status = ProcessingStatus.OK.value
    rating = words_number = None
    try:
        async with aiohttp.ClientSession() as session:
            article_text = await fetch(session, url, fetch_timeout)

            article_text = SANITIZERS['inosmi_ru'](article_text, True)

            with check_time(url):
                words = await text_tools.split_by_words(
                    morph,
                    article_text,
                    analysis_timeout
                )
            rating = text_tools.calculate_jaundice_rate(
                words,
                charged_words
            )
            words_number = len(words)
    except aiohttp.ClientError:
        status = ProcessingStatus.FETCH_ERROR.value
    except adapters.ArticleNotFound:
        status = ProcessingStatus.PARSING_ERROR.value
    except asyncio.TimeoutError:
        status = ProcessingStatus.TIMEOUT.value

    articles_cards.append(
        {
            'url': url,
            'status': status,
            'rating': rating,
            'words_number': words_number}
    )


def test_process_article():
    charged_words = ['беспокойство', ' грязь', 'кризис']
    morph = pymorphy2.MorphAnalyzer()

    url = 'https://inosmi.ru/not/exist.html'
    articles_cards = []
    asyncio.run(process_article(url, charged_words, articles_cards, morph))
    assert articles_cards[0]['status'] == ProcessingStatus.FETCH_ERROR.value

    url = 'https://lenta.ru/news/2022/11/27/20_strausov/'
    articles_cards = []
    asyncio.run(process_article(url, charged_words, articles_cards, morph))
    assert articles_cards[0]['status'] == ProcessingStatus.PARSING_ERROR.value

    url = 'https://inosmi.ru/20221104/mars-257472040.html'
    articles_cards = []
    asyncio.run(
        process_article(
            url,
            charged_words,
            articles_cards,
            morph,
            fetch_timeout=0.1
        )
    )
    assert articles_cards[0]['status'] == ProcessingStatus.TIMEOUT.value

    url = 'https://inosmi.ru/20221104/mars-257472040.html'
    articles_cards = []
    asyncio.run(
        process_article(
            url,
            charged_words,
            articles_cards,
            morph,
            analysis_timeout=0.1
        )
    )
    assert articles_cards[0]['status'] == ProcessingStatus.TIMEOUT.value


async def handle(request, charged_words, max_urls):
    urls = request.query.getone('urls', None)
    if not urls:
        return web.json_response({'error': 'no urls to analyze'}, status=400)

    urls = urls.split(sep=',')
    if len(urls) > max_urls:
        return web.json_response(
            {'error': f'too many urls in request, should be {max_urls} or less'},
            status=400,
        )

    morph = pymorphy2.MorphAnalyzer()
    articles_cards = []
    async with anyio.create_task_group() as task_group:
        for url in urls:
            task_group.start_soon(
                process_article,
                url,
                charged_words,
                articles_cards,
                morph,
            )

    return web.json_response(articles_cards)


def main():
    args_parser = create_args_parser()
    args = args_parser.parse_args()
    logging.basicConfig()
    logger.setLevel(logging.INFO)

    charged_words = []
    charged_words_path = 'charged_dict'
    for file_name in os.listdir(charged_words_path):
        file_path = os.path.join(charged_words_path, file_name)
        with open(file_path, mode='r', encoding="UTF-8") as file:
            for word in file:
                charged_words.append(word.strip())

    handler = functools.partial(
        handle,
        charged_words=charged_words,
        max_urls=args.max_urls,
    )
    app = web.Application()
    app.add_routes([web.get('/', handler)])
    web.run_app(app)


if __name__ == '__main__':
    main()
