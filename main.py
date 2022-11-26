import aiohttp
import asyncio
from adapters import SANITIZERS


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


async def main():
    async with aiohttp.ClientSession() as session:
        url = 'https://inosmi.ru/20221106/kosmos-257523048.html'
        article_text = await fetch(session, url)
        article_text = SANITIZERS['inosmi_ru'](article_text, True)
        print(article_text)

if __name__ == '__main__':
    asyncio.run(main())
