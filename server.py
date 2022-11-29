from aiohttp import web


async def handle(request):
    urls = request.query.getone('urls', None)
    response = None
    if urls:
        response = {
            'urls': urls.split(sep=',')
        }

    return web.json_response(response)


def main():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    web.run_app(app)


if __name__ == '__main__':
    main()
