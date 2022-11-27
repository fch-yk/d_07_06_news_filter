import asyncio
import os


import aiohttp
import aiofiles
import pymorphy2

import text_tools
from adapters import SANITIZERS


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


async def main():
    charged_words = []
    charged_dict_path = 'charged_dict'
    for file_name in os.listdir(charged_dict_path):
        file_path = os.path.join(charged_dict_path, file_name)
        async with aiofiles.open(file_path, mode='r') as file:
            async for word in file:
                charged_words.append(word.strip())

    async with aiohttp.ClientSession() as session:
        url = 'https://inosmi.ru/20221106/kosmos-257523048.html'
        article_text = await fetch(session, url)
        article_text = SANITIZERS['inosmi_ru'](article_text, True)
        morph = pymorphy2.MorphAnalyzer()
        words = text_tools.split_by_words(morph, article_text)
        jaundice_rate = text_tools.calculate_jaundice_rate(
            words,
            charged_words
        )
        print(f'Raiting: {jaundice_rate}')
        print(f'Words in the article: {len(words)}')

if __name__ == '__main__':
    asyncio.run(main())
