import asyncio
import os
from enum import Enum

import aiofiles
import aiohttp
import anyio
import pymorphy2

import text_tools
from adapters import SANITIZERS


class ProcessingStatus(Enum):
    OK = 'OK'
    FETCH_ERROR = 'FETCH_ERROR'


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


async def process_article(url, charged_words, articles_cards):
    status = ProcessingStatus.OK
    rating = words_number = None
    try:
        async with aiohttp.ClientSession() as session:
            article_text = await fetch(session, url)
            article_text = SANITIZERS['inosmi_ru'](article_text, True)
            morph = pymorphy2.MorphAnalyzer()
            words = text_tools.split_by_words(morph, article_text)
            rating = text_tools.calculate_jaundice_rate(
                words,
                charged_words
            )
            status = ProcessingStatus.OK
            words_number = len(words)
    except (aiohttp.ClientError,):
        status = ProcessingStatus.FETCH_ERROR

    articles_cards.append(
        {
            'url': url,
            'status': status,
            'rating': rating,
            'words_number': words_number}
    )


async def main():
    charged_words = []
    charged_dict_path = 'charged_dict'
    for file_name in os.listdir(charged_dict_path):
        file_path = os.path.join(charged_dict_path, file_name)
        async with aiofiles.open(file_path, mode='r') as file:
            async for word in file:
                charged_words.append(word.strip())

    test_articles = [
        'https://inosmi.ru/not/exist.html',
        'https://inosmiy.ru/20221106/virusy-257514193.html',
        'https://inosmi.ru/20221106/videoigry-257474918.html',
        'https://inosmi.ru/20221106/kosmos-257489166.html',
        'https://inosmi.ru/20221104/mars-257472040.html'
    ]

    articles_cards = []
    async with anyio.create_task_group() as task_group:
        for url in test_articles:
            task_group.start_soon(
                process_article,
                url,
                charged_words,
                articles_cards,
            )

    for article_card in articles_cards:
        print(
            f'URL: {article_card["url"]}',
            f'Status: {article_card["status"]}',
            f'Rating: {article_card["rating"]}',
            f'Words in the article: {article_card["words_number"]}',
            sep='\n',
            end='\n'*2
        )


if __name__ == '__main__':
    asyncio.run(main())
