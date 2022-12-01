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


class ProcessingStatus(Enum):
    OK = 'OK'
    FETCH_ERROR = 'FETCH_ERROR'
    PARSING_ERROR = 'PARSING_ERROR'
    TIMEOUT = 'TIMEOUT'


@contextmanager
def check_time(url):
    start = time.monotonic()
    try:
        yield
    finally:
        logger = logging.getLogger("check_time")
        end = time.monotonic()
        total = round(end - start, 2)
        logger.info(
            'The analysis of the text from %s was completed in %s seconds',
            url,
            total
        )


async def fetch(session, url):
    async with async_timeout.timeout(5):
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.text()


async def process_article(url, charged_words, articles_cards):
    status = ProcessingStatus.OK.value
    rating = words_number = None
    try:
        async with aiohttp.ClientSession() as session:
            article_text = await fetch(session, url)

            article_text = SANITIZERS['inosmi_ru'](article_text, True)
            morph = pymorphy2.MorphAnalyzer()

            with check_time(url):
                words = await text_tools.split_by_words(morph, article_text)
            rating = text_tools.calculate_jaundice_rate(
                words,
                charged_words
            )
            words_number = len(words)
    except (
        aiohttp.ClientError,
        adapters.ArticleNotFound,
        asyncio.TimeoutError
    ) as error:
        if isinstance(error, aiohttp.ClientError):
            status = ProcessingStatus.FETCH_ERROR.value
        elif isinstance(error, adapters.ArticleNotFound):
            status = ProcessingStatus.PARSING_ERROR.value
        else:
            status = ProcessingStatus.TIMEOUT.value

    articles_cards.append(
        {
            'url': url,
            'status': status,
            'rating': rating,
            'words_number': words_number}
    )


async def handle(request, charged_words):
    urls = request.query.getone('urls', None)
    if not urls:
        return web.json_response({'error': 'no urls to analyze'}, status=400)

    urls = urls.split(sep=',')
    max_urls = 10
    if len(urls) > max_urls:
        return web.json_response(
            {'error': 'too many urls in request, should be 10 or less'},
            status=400,
        )

    articles_cards = []
    async with anyio.create_task_group() as task_group:
        for url in urls:
            task_group.start_soon(
                process_article,
                url,
                charged_words,
                articles_cards,
            )

    return web.json_response(articles_cards)


def main():
    logging.basicConfig()
    logger = logging.getLogger("check_time")
    logger.setLevel(logging.DEBUG)

    charged_words = []
    charged_words_path = 'charged_dict'
    for file_name in os.listdir(charged_words_path):
        file_path = os.path.join(charged_words_path, file_name)
        with open(file_path, mode='r', encoding="UTF-8") as file:
            for word in file:
                charged_words.append(word.strip())

    handler = functools.partial(handle, charged_words=charged_words)
    app = web.Application()
    app.add_routes([web.get('/', handler)])
    web.run_app(app)


if __name__ == '__main__':
    main()
