# Copyright (c) James Gardner 2024 All Rights Reserved
# This file is licensed under the GNU Lesser General Public License (LGPL) v3.0.
# You may obtain a copy of the license at http://www.gnu.org/licenses/lgpl-3.0.html.
# 
# This software is distributed WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License
# for more details.

"""
CSRF protection is a trade-off between giving an ergonomic experience to users and developers, and security.

To have complete security you can block all requests, but that doesn't make an interesting app. Or you create a new token for every screen and only allow the user to submit one form at once, but that breaks browser navigation.

This implementation errs on the side of being ergonomic. Specificially it will re-issue the same token with a different signature under the following circumstances:

* It notices that a session is now in place when before there was none - this means that if a user starts filling in a form before logging in, they can still submit it after logging in because the CSRF token won't change when the new CSRF token bundle is produced
* It notices that some time has passed since the cookie was issued, but that the cookie is still valid and the session is unchanged so it re-issues the cookie with a new expiry - this means that as long as the session is still valid, and the CSRF token bundle hasn't expired completely, the same CSRF token will be avalable to the application, so forms will still submit if a new cookie is issued since they were generated and the CSRF token will only stop working if the session changes.

It implements rate limiting so that only so many tokens can be signed in a specified interval.

It is fairly strict with what it expects and will raise an exception if:

* The request is not http

It will return forbidden if:

* The content-type is not `application/x-www-form-urlencoded` if there is a body

It will also assume that any request that comes through with a body could potentially change state, and therefore will contain a CSRF token. This applied even in methods like GET where there shouldn't be a body.

For these reasons, this middleware should be kept very close to the application it is protecting, and not wrap more than it needs.

The CSRF token can be shared by multiple instances of this middleware wrapped around different parts of your application as long as the settings are the same for each.


In terms of technical implementation:

We have pure ASGI middleware, no starlette, no methods except __init__ and __call__. We use the Python standard library for cookie handling.

The CSRF Token Bundle is as follows:

csrftoken.session_id.timestamp.signature

The CSRF token set here come from os.urandom(32) urlsafe-base64 encoded and then stripped of padding and new CSRF token bundles are rate limited.

At the start of __call__ we try to load the CSRF Token Bundle from the cookie to obtain the expected CSRF token and we also try to load the CSRF token from any body, no matter what the method is.

The __init__ takes a get_session_from_scope() function as an argument. On each request the session is fetched using this function.

During processing we might set next_csrf_token_bundle to a new cookie value. The cookie appended to any existing cookies that are sent on the response.

If the token is still valid but renew_after_ms milliseconds have passed and the session is still the same, we issue a new token with the same CSRF token and set the next_csrf_token_bundle variable

If the token has no session but now there is one, we re-issue the cookie with the same CSRF token, setting next_csrf_token_bundle.

If there is no CSRF token bundle in the cookie or if the fetched token has an invalid signature or has expired we set the next_csrf_token_bundle variable to a new CSRF token bundle with a new CSRF token. This creates a new CSRF token in the bundle meaning any existing forms will fail submission due to the changed CSRF token.

If the session from the cookie's CSRF token bundle doesn't match the current session we return a forbidden message.

If the CSRF token from the body doesn't match the value from the CSRF token bundle or if either are missing or shoreter than expected, we return a forbidden message.

If the request is not HTTP or if there is a body and the content type is not application/x-www-form-urlencoded we return a forbidden message.

Otherwise we call the app setting the csrf token to scope['csrf'] and setting the receive method to have the body that we parsed earlier so that the app can parse the form again.

The cookies should not work sub-domain (so we explicitly don't set the domain otherwise sub-domains are also enabled), should not be accessible from JavaScript (so we set httponly, but if you want AJAX support you should not set this or JavaScript will not be able to read the CSRF token), should have same site, have a max age that result in the expirt of the CSRF token bundle expiry time, and be secure if the app is not in dev mode. This means secure and http-only need to be arguments to __init__ too.

If multiple csrftoken variables are posted in the body, only the first is used, the rest are ignored.

Rate limiting works by appending the current time of each signing attempt to a deque, then removing any entries from outside the last second and finally comparing the length of the deque with the max number of signing requests allowed per second set in __init__.


This means we have CSRF nicely wrapped up in middleware, the ability to link the CSRF token to the session, the ability to renew CSRF tokens without changing the token.

More info:

* https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html#login-csrf
"""


import sys
if sys.implementation.name == 'micropython':
    sys.path.append('micropython')

import time
import hashlib
import hmac
import base64
from http.cookies import SimpleCookie
from collections import deque


import sys
if sys.implementation.name == 'micropython':

    # os.urandom
    import random
    def urandom(n):
        """Generate `n` random bytes using random.getrandbits()"""
        return bytes(random.getrandbits(8) for _ in range(n))


    # urllib.parse_qs
    def parse_qs(query):
        """Parses a query string into a dictionary of lists."""
        params = {}

        # Split the query string by '&' to separate key-value pairs
        pairs = query.split('&')

        for pair in pairs:
            if '=' in pair:
                key, value = pair.split('=', 1)
                key = unquote(key)
                value = unquote(value)

                # If the key is already in the dictionary, append the value to the list
                if key in params:
                    params[key].append(value)
                else:
                    # Otherwise, create a new list for this key
                    params[key] = [value]
            elif pair:
                # Handle cases where there is a key without a value
                key = unquote(pair)
                if key in params:
                    params[key].append('')
                else:
                    params[key] = ['']

        return params

    def unquote(string):
        """Unquote a percent-encoded string (e.g., 'Hello%20World' -> 'Hello World')."""
        res = []
        i = 0
        while i < len(string):
            if string[i] == '%' and i + 2 < len(string):
                # Decode the percent-encoded character
                hex_value = string[i+1:i+3]
                res.append(chr(int(hex_value, 16)))
                i += 3
            else:
                # Append normal character
                res.append(string[i])
                i += 1
        return ''.join(res)


else:
    from os import urandom
    from urllib.parse import parse_qs


class CSRFMiddleware:
    def __init__(self, app, secret, get_session_from_scope=lambda x: '', token_ttl=3_600, renew_after=600, secure=True, http_only=True, max_tokens_per_interval=20, interval_ms=1000):
        self.app = app
        self.get_session_from_scope = get_session_from_scope
        self.secret = secret
        self.token_ttl_ms = token_ttl * 1000
        self.renew_after_ms = renew_after * 1000
        self.secure = secure
        self.http_only = http_only
        self.token_signing_times = deque()
        self.max_tokens_per_interval = max_tokens_per_interval
        self.interval_ms = interval_ms

    def generate_csrf_token_bundle(self, session_id, re_use_csrf_token=None):
        current_time = time.time()
        self.enforce_rate_limit(current_time)
        timestamp = str(int(current_time * 1000))
        if re_use_csrf_token is None:
            csrf_token = base64.urlsafe_b64encode(urandom(32)).decode('utf-8').rstrip('=')
        else:
            csrf_token = re_use_csrf_token
        signature = hmac.new(self.secret.encode(), f"{csrf_token}.{session_id}.{timestamp}".encode(), hashlib.sha256).hexdigest()
        return f"{csrf_token}.{session_id}.{timestamp}.{signature}"

    def enforce_rate_limit(self, current_time):
        # Remove old timestamps outside the rate limit window (e.g., 1 second)
        while self.token_signing_times and self.token_signing_times[0] < current_time - (self.interval_ms/1000.0):
            self.token_signing_times.popleft()

        # Enforce the rate limit globally
        if len(self.token_signing_times) >= self.max_tokens_per_interval:
            raise Exception("Rate limit exceeded for CSRF token signing")
        self.token_signing_times.append(current_time)
        print(self.token_signing_times, self.max_tokens_per_interval, self.interval_ms)

    def validate_token(self, token):
        try:
            random_data, session_id, timestamp, signature = token.split('.')
            expected_signature = hmac.new(self.secret.encode(), f"{random_data}.{session_id}.{timestamp}".encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected_signature):
                return False
            if int(time.time() * 1000) > int(timestamp) + self.token_ttl_ms:
                return False
            return True
        except ValueError:
            return False

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            raise Exception('Only for HTTP')

        body = await self.receive_body(receive)
        required = False
        if bool(body) or scope['method'] not in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
            required = True

        content_type = dict(scope.get('headers', [])).get(b'content-type', b'').lower()
        if required and content_type != b'application/x-www-form-urlencoded':
            await self.forbidden_response(send)
            return

        form_data = parse_qs(body.decode('utf-8')) if body else {}
        form_csrf_token = form_data.get('csrftoken', [None])[0]

        cookies = self.parse_cookies(scope.get('headers', []))
        csrf_token_bundle = cookies.get('csrf_token_bundle')

        session_id = self.get_session_from_scope(scope)

        next_csrf_token_bundle = None
        token_validity = False
        cookie_csrf_token = None
        cookie_session_id = None

        if csrf_token_bundle:
            token_validity = self.validate_token(csrf_token_bundle)
            if token_validity:
                cookie_csrf_token, cookie_session_id, cookie_timestamp, cookie_signature = csrf_token_bundle.split('.')
                now = time.time()
                print('>', 'now:', now, 'int(now * 1000):', int(now * 1000), 'cookie_timestamp:', cookie_timestamp, 'renew_after_ms:', self.renew_after_ms)
                if (int(now * 1000) > int(cookie_timestamp) + self.renew_after_ms and (cookie_session_id == '' or cookie_session_id == session_id)) or (cookie_session_id == '' and session_id != cookie_session_id):
                    next_csrf_token_bundle = self.generate_csrf_token_bundle(session_id, re_use_csrf_token=cookie_csrf_token)
        else:
            next_csrf_token_bundle = self.generate_csrf_token_bundle(session_id)

        print('csrf_token_bundle:', csrf_token_bundle, ', token_validity:', token_validity, ', next_csrf_token_bundle:', next_csrf_token_bundle, 'required:', required, 'cookie_csrf_token:', cookie_csrf_token, 'form_csrf_token:', form_csrf_token, 'cookie_session_id:', cookie_session_id, 'session_id:', session_id, 'body:', body, 'form_data:', form_data)
        if required and (not cookie_csrf_token or not form_csrf_token or cookie_csrf_token != form_csrf_token or (cookie_session_id != '' and cookie_session_id != session_id)):
            await self.forbidden_response(send)
            return

        if cookie_csrf_token:
            scope['csrf'] = cookie_csrf_token
        else:
            scope['csrf'] = next_csrf_token_bundle.split('.')[0]

        receive = self.wrap_receive(receive, body)

        async def send_wrapper(message):
            if message['type'] == 'http.response.start' and next_csrf_token_bundle:
                headers = message.setdefault('headers', [])
                cookie = SimpleCookie()
                cookie['csrf_token_bundle'] = next_csrf_token_bundle
                cookie['csrf_token_bundle']['path'] = '/'
                if self.http_only:
                    cookie['csrf_token_bundle']['httponly'] = True
                if self.secure:
                    cookie['csrf_token_bundle']['secure'] = True
                cookie['csrf_token_bundle']['samesite'] = 'Strict'
                cookie['csrf_token_bundle']['max-age'] = int(self.token_ttl_ms/1000.0)
                new_cookie_header = cookie.output(header='', sep='').encode('utf-8').strip()
                for i, (name, value) in enumerate(headers):
                    if name.lower() == b'set-cookie':
                        headers[i] = (name, value + b', ' + new_cookie_header)
                        break
                else:
                    headers.append((b'set-cookie', new_cookie_header))
            await send(message)

        await self.app(scope, receive, send_wrapper)

    def parse_cookies(self, headers):
        cookie_header = next((value for key, value in headers if key == b'cookie'), b'')
        cookies = SimpleCookie(cookie_header.decode('latin1'))
        return {key: morsel.value for key, morsel in cookies.items()}

    async def receive_body(self, receive):
        body = b''
        more_body = True
        while more_body:
            message = await receive()
            body += message.get('body', b'')
            more_body = message.get('more_body', False)
        return body

    def wrap_receive(self, receive, body):
        async def receive_wrapper():
            return {
                'type': 'http.request',
                'body': body,
                'more_body': False
            }
        return receive_wrapper

    async def forbidden_response(self, send):
        response_headers = [
            (b'content-type', b'text/plain; charset=utf-8'),
        ]
        response_body = b'403 Forbidden'
        await send({
            'type': 'http.response.start',
            'status': 403,
            'headers': response_headers,
        })
        await send({
            'type': 'http.response.body',
            'body': response_body,
        })
