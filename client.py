import argparse
import asyncio
import pprint

import aiohttp


def create_args_parser():
    parser = argparse.ArgumentParser(description='Jaundice news rate')
    default_urls = [
        'https://inosmi.ru/not/exist.html',
        'https://inosmiy.ru/20221106/virusy-257514193.html',
        'https://inosmi.ru/20221106/videoigry-257474918.html',
        'https://lenta.ru/news/2022/11/27/20_strausov/',
        'https://inosmi.ru/20221104/mars-257472040.html',
        'https://inosmi.ru/20221127/bessmertie-258272850.html'
    ]
    default_urls = ','.join(default_urls)
    parser.add_argument(
        '--urls',
        default=default_urls,
        metavar='{urls of articles from inosmi.ru}',
        help=(
            'The urls of articles to rate separated by commas, '
            f'by default: {default_urls}'
        ),
    )
    return parser


async def main():
    args_parser = create_args_parser()
    args = args_parser.parse_args()

    server_url = 'http://127.0.0.1:8080/'
    payload = {'urls': args.urls}
    async with aiohttp.ClientSession() as session:
        async with session.get(server_url, params=payload) as response:
            response.raise_for_status()
            articles_cards = await response.json()
            pprint.pprint(articles_cards)


if __name__ == '__main__':
    asyncio.run(main())
