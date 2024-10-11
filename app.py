# Copyright (c) James Gardner 2024 All Rights Reserved
# This file is licensed under the GNU Lesser General Public License (LGPL) v3.0.
# You may obtain a copy of the license at http://www.gnu.org/licenses/lgpl-3.0.html.
# 
# This software is distributed WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License
# for more details.

import static
import staticgz
import basicauth
import fileio
from sitemap import Section, Page, NavMiddleware
from tags import Template, tag, Placeholder


page = Template(
    tag('html', {'lang': 'en'}, [
        tag('head', {}, [
            tag('title', {}, Placeholder('title')),
            tag('meta', {'name': "viewport", 'content': "width=device-width, initial-scale=1.0"}),
            tag('meta', {'charset': "UTF-8"}),
            tag('link', {'rel': "stylesheet", 'href':"/nav.css"}),
        ]),
        tag('body', {}, [
            tag('input', {'type':"checkbox", 'id': "nav-toggle"}),
            tag('label', {'class': "hamburger", 'for': "nav-toggle"}, [
              tag('div', {}, ''),
              tag('div', {}, ''),
            ]),
            tag('div', {'class': 'nav-container'}, Placeholder('nav')),
            tag('article', {}, [
                tag('h1', {}, Placeholder('title')),
                tag('p', {}, [Placeholder('title')]),
                Placeholder('body'),
            ])
        ])
    ])
)


async def app(scope, receive, send):
    # assert scope["path"] == "/hello.html", scope["path"]
    # assert scope["query_string"] == b"a=1&a=2&b=3", scope["query_string"]
    msg = page.render(
        title='This is the title',
        nav=tag([
            scope['nav'].main_nav(),
            scope['nav'].breadcrumbs(),
            scope['nav'].section_nav(),
        ]),
        body=tag('p', {}, 'Hello, world')
    ).encode('utf8')
    body = await receive()
    if scope["method"] == "POST":
        assert (
            body["body"] == b"hi"
        ), f'Expected body to be b"hi" but got, {body["body"]}'
        assert body["type"] == "http.request"
        assert body["more_body"] == False
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"Content-Type", b"text/html"),
                (b"Content-Length", str(len(msg)).encode("ascii")),
            ],
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": msg,
        }
    )



application = staticgz.StaticGzipMiddleware(
    static.StaticFilesMiddleware(
        NavMiddleware(
            app,
            Section('Home', [
                Page('Home', '/'),
                Page('Main', '/main'),
                Section('About', [
                    Page('About', '/about', [
                        Page('Details', '/about/details'),
                        Section('Hello', [
                            Page('Hello', '/hello.html'),
                        ])
                    ])
                ])
            ])
        ),
        'www',
        'mimetypes.json',
    ),
    'wwwgz',
    'wwwgz.json'
)
# basicauth.BasicAuthMiddleware(
#     'username',
#     'password'
# )
