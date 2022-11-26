import aiohttp
import asyncio


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


async def main():
    async with aiohttp.ClientSession() as session:
        url = 'https://inosmi.ru/20221106/kosmos-257523048.html'
        html = await fetch(session, url)
        print(html)

if __name__ == '__main__':
    asyncio.run(main())
