# Copyright (c) James Gardner 2024 All Rights Reserved
# This file is licensed under the GNU Lesser General Public License (LGPL) v3.0.
# You may obtain a copy of the license at http://www.gnu.org/licenses/lgpl-3.0.html.
# 
# This software is distributed WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License
# for more details.

import unittest
from unittest.mock import AsyncMock, patch
from security import SecurityHeadersMiddleware


async def app(scope, receive, send):
    assert scope['type'] == 'http'
    response_headers = [
        (b'content-type', b'text/html'),
    ]
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': response_headers,
    })
    await send({
        'type': 'http.response.body',
        'body': 'ok'.encode('utf-8'),
    })


class TestSecurityHeadersMiddleware(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.app = app
        self.middleware = SecurityHeadersMiddleware(self.app)

    async def simulate_request(self, path, headers=None):
        headers = headers or []
        scope = {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": headers,
        }
        receive = AsyncMock()
        send = AsyncMock()

        # Call the middleware
        await self.middleware(scope, receive, send)

        return send

    async def test_security_headers(self):
        send = await self.simulate_request("/")

        # Ensure the send function was called at least once
        self.assertGreater(len(send.mock_calls), 0, "The send function was not called.")

        # Verify the security headers are present
        start_call = send.mock_calls[0]
        headers = dict(start_call[1][0]["headers"])

        expected_headers = {
            b"Content-Security-Policy": b"default-src 'self'; script-src 'self'; object-src 'none';",
            b"X-Content-Type-Options": b"nosniff",
            b"X-Frame-Options": b"SAMEORIGIN",
            b"X-XSS-Protection": b"1; mode=block",
            b"Referrer-Policy": b"no-referrer-when-downgrade",
            b"Permissions-Policy": b"geolocation=(), microphone=(), camera=()",
            # b"Strict-Transport-Security": b"max-age=31536000; includeSubDomains",
        }

        for header, value in expected_headers.items():
            self.assertIn(header, headers)
            self.assertEqual(headers[header], value)

        content_call = send.mock_calls[1]
        content = content_call[1][0]["body"]
        self.assertEqual(content, b'ok')
