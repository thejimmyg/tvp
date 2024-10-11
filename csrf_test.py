# Copyright (c) James Gardner 2024 All Rights Reserved
# This file is licensed under the GNU Lesser General Public License (LGPL) v3.0.
# You may obtain a copy of the license at http://www.gnu.org/licenses/lgpl-3.0.html.
# 
# This software is distributed WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License
# for more details.

"""
Explanation:
Test Setup: The setUp method initializes the CSRF middleware with a mock application.

Helper Methods:
* simulate_request is used to simulate an HTTP request, including headers, body, and cookies.
* get_csrf_cookie_and_token is used to perform a GET request to retrieve the CSRF cookie and token from the response.
* Test Cases:
* test_csrf_token_generation_on_get: Verifies that a CSRF token is generated during a GET request.
* test_csrf_token_in_cookie_on_get: Checks that the CSRF token is set in a cookie.
* test_form_submission_csrf_success: Ensures that form submission passes with a valid CSRF token.
* test_form_submission_csrf_failure: Verifies that form submission fails with an invalid CSRF token.
* test_no_csrf_cookie: Ensures that form submission fails if there is no CSRF cookie.
* test_no_csrf_token_in_form: Ensures that form submission fails if there is no CSRF token in the form.
* test_expired_csrf_token: Ensures that form submission fails if the CSRF token is expired.
* test_successful_csrf_token_renewal: Ensure that a token is renewed if the session is still valid, and that it is not otherwise
* test_token_reissue_on_session_creation: Tests the scenario where the token is reissued when a session is created.
* test_forbidden_if_request_is_not_http: Verifies that non-HTTP requests do not generate any HTTP response.
* test_forbidden_if_content_type_not_urlencoded: Ensures that requests with incorrect content type are forbidden.

These tests cover the core behaviors expected of the CSRF middleware as described in the docstring.
"""

import unittest
from urllib.parse import urlencode
from csrf import CSRFMiddleware
from unittest.mock import AsyncMock
import http.cookies
import time

import hmac
import hashlib
from unittest.mock import patch


class TestApp:
    """A simple test app to simulate downstream ASGI behavior."""
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            if scope["method"] == "GET" and scope["path"] == "/":
                response_body = b"""
                <html>
                <body>
                <form method="post">
                <input type="hidden" name="csrftoken" value="%s">
                </form>
                </body>
                </html>
                """ % scope["csrf"].encode()

                await send({
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"text/html")],
                })
                await send({
                    "type": "http.response.body",
                    "body": response_body,
                })
            elif scope["path"] == "/process":
                # Someone might send a GET with a body here
                await send({
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"text/plain")],
                })
                await send({
                    "type": "http.response.body",
                    "body": b"CSRF test passed",
                })
            else:
                await send({
                    "type": "http.response.start",
                    "status": 404,
                    "headers": [(b"content-type", b"text/plain")],
                })
                await send({
                    "type": "http.response.body",
                    "body": b"Not Found",
                })


class CSRFMiddlewareTest(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        secret = "supersecret"
        self.app = CSRFMiddleware(TestApp(), secret=secret, secure=False, get_session_from_scope=lambda x: '')

    async def simulate_request(self, path, method="GET", body=None, cookies=None):
        # Prepare headers
        headers = [
            (b"host", b"localhost"),
        ]

        if body:
            headers.append((b"content-type", b"application/x-www-form-urlencoded"))

        if cookies:
            cookie_header = "; ".join([f"{k}={v}" for k, v in cookies.items()])
            headers.append((b"cookie", cookie_header.encode('utf-8')))

        # Create an ASGI scope
        scope = {
            "type": "http",
            "method": method,
            "path": path,
            "headers": headers,
        }

        # Prepare the body and receive function
        if body:
            body_bytes = urlencode(body).encode('utf-8')
            receive = AsyncMock(return_value={
                "type": "http.request",
                "body": body_bytes,
                "more_body": False
            })
        else:
            receive = AsyncMock(return_value={
                "type": "http.request",
                "body": b"",
                "more_body": False
            })

        # Prepare the mock send function to capture the response
        send = AsyncMock()

        # Call the middleware with the prepared scope, receive, and send
        await self.app(scope, receive, send)

        # Capture the response start and body
        response_start = send.mock_calls[0][1][0] if send.mock_calls else None
        response_body = send.mock_calls[1][1][0]['body'] if len(send.mock_calls) > 1 else b""

        return response_start, response_body, send

    async def get_csrf_cookie_and_token(self):
        # Perform a GET request to retrieve the CSRF cookie and token
        response_start, response_body, send = await self.simulate_request("/")

        # Extract the Set-Cookie header from the response
        cookies = {}
        for header, value in response_start['headers']:
            if header == b'set-cookie':
                cookie_value = value.decode('utf-8')
                cookie = http.cookies.SimpleCookie(cookie_value)
                for key in cookie:
                    cookies[key] = cookie[key].value

        # Extract the CSRF token from the form in the response body
        csrf_token_start = response_body.find(b'name="csrftoken" value="') + len(b'name="csrftoken" value="')
        csrf_token_end = response_body.find(b'"', csrf_token_start)
        csrf_token = response_body[csrf_token_start:csrf_token_end].decode('utf-8')

        return cookies, csrf_token

    async def test_csrf_token_generation_on_get(self):
        response_start, response_body, send = await self.simulate_request("/")
        self.assertEqual(response_start["status"], 200)
        self.assertIn(b'csrftoken', response_body)

    async def test_csrf_token_in_cookie_on_get(self):
        response_start, response_body, send = await self.simulate_request("/")
        cookie_headers = [header for header, value in response_start["headers"] if header == b'set-cookie']
        self.assertTrue(cookie_headers, "CSRF token should be set in the cookie on GET requests.")

    async def test_form_submission_csrf_success(self):
        # Get the CSRF cookie and token from the form
        cookies, csrf_token = await self.get_csrf_cookie_and_token()

        # Simulate a POST request with the correct CSRF token
        form_data = {
            "csrftoken": csrf_token,
        }
        print(form_data, cookies)
        response_start, response_body, _ = await self.simulate_request("/process", method="POST", body=form_data, cookies=cookies)

        self.assertEqual(response_start['status'], 200, "CSRF validation should pass with a valid token")
        self.assertIn(b"CSRF test passed", response_body)

    async def test_form_submission_csrf_failure(self):
        # Get the CSRF cookie and token from the form
        cookies, csrf_token = await self.get_csrf_cookie_and_token()

        # Simulate a POST request with an incorrect CSRF token
        form_data = {
            "csrftoken": "invalid-token",
        }

        response_start, response_body, _ = await self.simulate_request("/process", method="POST", body=form_data, cookies=cookies)
        self.assertEqual(response_start['status'], 403, "CSRF failure should return a 403 status")

    async def test_no_csrf_cookie(self):
        # Simulate a POST request without a CSRF cookie
        form_data = {
            "csrftoken": "random-token",
        }

        response_start, response_body, _ = await self.simulate_request("/process", method="POST", body=form_data, cookies={})
        self.assertEqual(response_start['status'], 403, "CSRF check should fail if there is no CSRF cookie.")

    async def test_no_csrf_token_in_form(self):
        # Get the CSRF cookie and token from the form
        cookies, _ = await self.get_csrf_cookie_and_token()

        # Simulate a POST request without a CSRF token in the form
        response_start, response_body, _ = await self.simulate_request("/process", method="POST", body={}, cookies=cookies)
        self.assertEqual(response_start['status'], 403, "CSRF check should fail if there is no CSRF token in the form.")


    async def test_expired_csrf_token(self):
        # Get the CSRF cookie and token from the form
        cookies, csrf_token = await self.get_csrf_cookie_and_token()

        # Extract the session_id, timestamp, and signature
        token_parts = cookies['csrf_token_bundle'].split('.')
        csrf_token = token_parts[0]
        session_id = token_parts[1]
        timestamp = int(token_parts[2])
        signature = token_parts[3]

        # Create an expired timestamp by subtracting the expiration time from the current timestamp
        expired_timestamp = str(timestamp - (self.app.token_ttl_ms + 1))

        expired_signature = hmac.new(self.app.secret.encode(), f"{csrf_token}.{session_id}.{expired_timestamp}".encode(), hashlib.sha256).hexdigest()

        # Manually craft an expired CSRF token
        cookies = {'csrf_token_bundle': f"{csrf_token}.{session_id}.{expired_timestamp}.{expired_signature}"}

        # Simulate a POST request with the expired CSRF token
        form_data = {
            "csrftoken": csrf_token,
        }

        response_start, response_body, _ = await self.simulate_request("/process", method="POST", body=form_data, cookies=cookies)

        # Assert that the request is forbidden due to the expired token
        self.assertEqual(response_start['status'], 403, "CSRF validation should fail with an expired token")

    async def test_successful_csrf_token_renewal(self):
        # Set a short renew_after_ms period for testing purposes
        self.app.renew_after_ms = 1  # Renew after 1 millisecond

        for path, method, send_body in [
            ("/", "GET", False),
            ("/process", "POST", True),
            ("/process", "GET", True),
        ]:
            # Simulate a GET request to get the initial CSRF cookie and token
            cookies, csrf_token = await self.get_csrf_cookie_and_token()

            # Extract the original session_id, timestamp, and signature from the CSRF token bundle
            original_csrf_token, original_session_id, original_timestamp, original_signature = cookies['csrf_token_bundle'].split('.')

            # Wait for the renewal period to pass
            time.sleep((self.app.renew_after_ms+1)/1000.0)

            # Prepare the request data
            form_data = None
            if send_body:
                form_data = {
                    "csrftoken": csrf_token,
                }

            # Simulate the request after the renewal period
            response_start, response_body, _ = await self.simulate_request(
                path,
                method=method,
                body=form_data,
                cookies=cookies
            )

            # Ensure the request succeeded and a new CSRF token bundle is issued
            self.assertEqual(response_start['status'], 200, "CSRF validation should pass and renew the token")

            # Extract the Set-Cookie header from the response
            new_cookie_headers = [header for header, value in response_start["headers"] if header == b'set-cookie']

            # Parse the new cookies
            new_cookies = {}
            for header, value in response_start["headers"]:
                if header == b'set-cookie':
                    cookie_value = value.decode('utf-8')
                    cookie = http.cookies.SimpleCookie(cookie_value)
                    for key in cookie:
                        new_cookies[key] = cookie[key].value

            # Extract the new CSRF token and session_id from the reissued cookie
            print('===', new_cookies)
            new_csrf_token_bundle = new_cookies['csrf_token_bundle']
            new_csrf_token, new_session_id, new_timestamp, new_signature = new_csrf_token_bundle.split('.')

            # Ensure the session ID remains unchanged
            self.assertEqual(original_session_id, new_session_id, "The session ID should remain unchanged after renewal")

            # Ensure the CSRF token itself remains unchanged
            self.assertEqual(original_csrf_token, new_csrf_token, "The CSRF token should remain the same after renewal")

            # Ensure the timestamp is updated to a newer value
            self.assertGreater(new_timestamp, original_timestamp, "The timestamp should be updated in the new CSRF token bundle")

            # Ensure that the signature is correctly regenerated for the renewed token
            expected_signature = hmac.new(self.app.secret.encode(), f"{new_csrf_token}.{new_session_id}.{new_timestamp}".encode(), hashlib.sha256).hexdigest()
            self.assertEqual(new_signature, expected_signature, "The signature should match the expected signature for the renewed CSRF token bundle")

        # Put the default back
        self.app.renew_after_ms = 600_000


    async def test_token_reissue_on_session_creation(self):
        for path, method, send_body in [
            ("/", "GET", False),
            ("/process", "POST", True),
            ("/process", "GET", True),
        ]:
            self.app.get_session_from_scope = lambda x: ''
            # Simulate a GET request to get the initial CSRF cookie and token
            cookies, csrf_token = await self.get_csrf_cookie_and_token()

            # Extract the original session_id, timestamp, and signature
            original_csrf_token, original_session_id, original_timestamp, original_signature = cookies['csrf_token_bundle'].split('.')
            self.assertEqual(original_session_id, '', "The original session ID should be ''")

            # Simulate a new session creation by modifying the session ID
            self.app.get_session_from_scope = lambda x: 'new-session-id'

            form_data = None
            if send_body:
                form_data = {
                    "csrftoken": csrf_token,
                }

            response_start, response_body, _ = await self.simulate_request(
                path,
                method=method,
                body=form_data,
                cookies=cookies
            )

            # Ensure the request succeeded since the CSRF token hasn't changed
            self.assertEqual(response_start['status'], 200, "CSRF validation should pass with the original token after session creation")

            # Extract the Set-Cookie header from the response
            new_cookie_headers = [header for header, value in response_start["headers"] if header == b'set-cookie']

            # Parse the new cookies
            new_cookies = {}
            for header, value in response_start["headers"]:
                if header == b'set-cookie':
                    cookie_value = value.decode('utf-8')
                    cookie = http.cookies.SimpleCookie(cookie_value)
                    for key in cookie:
                        new_cookies[key] = cookie[key].value

            print(response_start["headers"])
            # Extract the new CSRF token and session_id from the reissued cookie
            new_csrf_token_bundle = new_cookies['csrf_token_bundle']
            new_csrf_token, new_session_id, new_timestamp, new_signature = new_csrf_token_bundle.split('.')
            self.assertEqual(new_session_id, 'new-session-id', "The session ID in the new CSRF token bundle should match the new session ID")

            # Ensure the CSRF token (without session ID) is unchanged
            self.assertEqual(original_csrf_token, new_csrf_token, "The CSRF token should remain the same after session creation")

            # Ensure the session ID is updated
            self.assertNotEqual(original_session_id, new_session_id, "The session ID should be updated in the new CSRF token bundle")

            self.assertGreaterEqual(new_timestamp, original_timestamp, "The timestamp for the new CSRF token bundle should be greater than or equal to the original")
            # Ensure that the signature is correctly regenerated for the new session ID
            expected_signature = hmac.new(self.app.secret.encode(), f"{new_csrf_token}.{new_session_id}.{new_timestamp}".encode(), hashlib.sha256).hexdigest()
            self.assertEqual(new_signature, expected_signature, "The signature should match the expected signature for the new session ID")

        # Put the default back
        self.app.get_session_from_scope = lambda x: ''

    async def test_forbidden_if_request_is_not_http(self):
        # Simulate a non-HTTP request
        scope = {
            "type": "websocket",  # Non-HTTP request type
            "path": "/",
            "headers": [],
        }
        receive = AsyncMock(return_value={"type": "websocket.connect"})
        send = AsyncMock()

        with self.assertRaises(Exception) as context:
            await self.app(scope, receive, send)

        self.assertEqual(str(context.exception), 'Only for HTTP', "Non-HTTP requests should raise 'Only for HTTP' exception")

    async def test_forbidden_if_content_type_not_urlencoded(self):
        # Get the CSRF cookie and token from the form
        cookies, csrf_token = await self.get_csrf_cookie_and_token()

        # Simulate a POST request with the correct CSRF token but wrong content type
        form_data = {
            "csrftoken": csrf_token,
        }

        # Prepare headers with incorrect content type
        headers = [
            (b"host", b"localhost"),
            (b"content-type", b"application/json"),
        ]

        cookie_header = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        headers.append((b"cookie", cookie_header.encode('utf-8')))

        # Create an ASGI scope
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/process",
            "headers": headers,
        }

        # Prepare the body and receive function
        body_bytes = urlencode(form_data).encode('utf-8')
        receive = AsyncMock(return_value={
            "type": "http.request",
            "body": body_bytes,
            "more_body": False
        })

        # Prepare the mock send function to capture the response
        send = AsyncMock()

        # Call the middleware with the prepared scope, receive, and send
        await self.app(scope, receive, send)

        # Capture the response start and body
        response_start = send.mock_calls[0][1][0] if send.mock_calls else None

        self.assertEqual(response_start['status'], 403, "CSRF protection should forbid requests with incorrect content type.")

    async def test_rate_limiting(self):
        # Adjust the rate limit for the test (e.g., 3 requests per second)
        self.app.max_tokens_per_interval = 3
        self.app.interval_ms = 50

        # Simulate multiple POST requests to trigger rate limiting
        for i in range(3):
            response_start, response_body, _ = await self.simulate_request(
                "/",
                method="GET",
                body=None,
                cookies={}  # Empty cookies to trigger signing
            )
            self.assertEqual(response_start['status'], 200, "CSRF validation should pass within rate limit")

        # The fourth request should trigger rate limiting, so we expect an exception
        with self.assertRaises(Exception) as context:
            await self.simulate_request(
                "/",
                method="GET",
                body=None,
                cookies={}  # Empty cookies to trigger signing
            )

        # Ensure the exception message is what we expect for rate limiting
        self.assertIn('Rate limit exceeded', str(context.exception))

        # Wait for the rate limit window to reset
        time.sleep((self.app.interval_ms+1)/1000.0)

        # Attempt the request again after the rate limit period
        response_start, response_body, _ = await self.simulate_request(
            "/",
            method="GET",
            body=None,
            cookies={}  # Empty cookies to trigger signing
        )
        self.assertEqual(response_start['status'], 200, "CSRF validation should pass after rate limit reset")

    # XXX Should the middleware expire the existing csrf token when the session changes? Ideally the user should do that explicitly so having the middleware do it might lead to more problems?

    # async def test_new_csrf_token_bundle_on_session_change(self):
    #     # Set a short renew_after_ms period for testing purposes
    #     self.app.renew_after_ms = 1  # Renew after 1 millisecond
    # 
    #     for path, method, send_body in [
    #         ("/", "GET", False),
    #         ("/process", "POST", True),
    #         ("/process", "GET", True),
    #     ]:
    #         # Simulate a GET request to get the initial CSRF cookie and token
    #         cookies, csrf_token = await self.get_csrf_cookie_and_token()
    # 
    #         # Extract the original session_id, timestamp, and signature from the CSRF token bundle
    #         original_csrf_token, original_session_id, original_timestamp, original_signature = cookies['csrf_token_bundle'].split('.')
    # 
    #         # Wait for the renewal period to pass
    #         time.sleep(2)
    # 
    #         # Simulate a new session creation by modifying the session ID
    #         self.app.get_session_from_scope = lambda x: 'new-session-id'
    # 
    #         # Prepare the request data
    #         form_data = None
    #         if send_body:
    #             form_data = {
    #                 "csrftoken": csrf_token,
    #             }
    # 
    #         # Simulate the request after the renewal period with a session change
    #         response_start, response_body, _ = await self.simulate_request(
    #             path,
    #             method=method,
    #             body=form_data,
    #             cookies=cookies
    #         )
    # 
    #         # Ensure the request succeeded and a new CSRF token bundle is issued
    #         self.assertEqual(response_start['status'], 200, "CSRF validation should pass and issue a new token")
    # 
    #         # Extract the Set-Cookie header from the response
    #         new_cookie_headers = [header for header, value in response_start["headers"] if header == b'set-cookie']
    # 
    #         # Parse the new cookies
    #         new_cookies = {}
    #         for header, value in response_start["headers"]:
    #             if header == b'set-cookie':
    #                 cookie_value = value.decode('utf-8')
    #                 cookie = http.cookies.SimpleCookie(cookie_value)
    #                 for key in cookie:
    #                     new_cookies[key] = cookie[key].value
    # 
    #         # Extract the new CSRF token and session_id from the reissued cookie
    #         new_csrf_token_bundle = new_cookies['csrf_token_bundle']
    #         new_csrf_token, new_session_id, new_timestamp, new_signature = new_csrf_token_bundle.split('.')
    # 
    #         # Ensure the session ID is updated
    #         self.assertNotEqual(original_session_id, new_session_id, "The session ID should be updated in the new CSRF token bundle")
    #         self.assertEqual(new_session_id, 'new-session-id', "The session ID in the new CSRF token bundle should match the new session ID")
    # 
    #         # Ensure the CSRF token itself is updated
    #         self.assertNotEqual(original_csrf_token, new_csrf_token, "A new CSRF token should be issued after session change")
    # 
    #         # Ensure the timestamp is updated to a newer value
    #         self.assertGreater(new_timestamp, original_timestamp, "The timestamp should be updated in the new CSRF token bundle")
    # 
    #         # Ensure that the signature is correctly regenerated for the new token and session ID
    #         expected_signature = hmac.new(self.app.secret.encode(), f"{new_csrf_token}.{new_session_id}.{new_timestamp}".encode(), hashlib.sha256).hexdigest()
    #         self.assertEqual(new_signature, expected_signature, "The signature should match the expected signature for the new CSRF token bundle")


if __name__ == "__main__":
    unittest.main()
