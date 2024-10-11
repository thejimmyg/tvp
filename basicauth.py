# Copyright (c) James Gardner 2024 All Rights Reserved
# This file is licensed under the GNU Lesser General Public License (LGPL) v3.0.
# You may obtain a copy of the license at http://www.gnu.org/licenses/lgpl-3.0.html.
# 
# This software is distributed WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License
# for more details.

import sys
if sys.implementation.name == 'micropython':
    sys.path.append('micropython')
from base64 import b64decode

class BasicAuthMiddleware:
    def __init__(self, app, username: str, password: str):
        self.app = app
        self.username = username
        self.password = password

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            headers = dict(scope['headers'])
            auth_header = headers.get(b'authorization', None)

            if auth_header is None:
                await self.send_401(send)
                return

            auth_type, auth_value = auth_header.decode().split(" ", 1)

            if auth_type.lower() != 'basic':
                await self.send_401(send)
                return

            decoded_auth = b64decode(auth_value).decode('utf-8')
            username, password = decoded_auth.split(":", 1)

            if username == self.username and password == self.password:
                await self.app(scope, receive, send)
            else:
                await self.send_401(send)
        else:
            raise Exception('Only http supported')

    async def send_401(self, send):
        headers = [
            (b'www-authenticate', b'Basic realm="Secure Area"'),
            (b'content-type', b'text/plain'),
            (b'content-length', b'12'),
        ]
        await send({
            'type': 'http.response.start',
            'status': 401,
            'headers': headers,
        })
        await send({
            'type': 'http.response.body',
            'body': b'Unauthorized',
        })
