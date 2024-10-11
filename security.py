# Copyright (c) James Gardner 2024 All Rights Reserved
# This file is licensed under the GNU Lesser General Public License (LGPL) v3.0.
# You may obtain a copy of the license at http://www.gnu.org/licenses/lgpl-3.0.html.
# 
# This software is distributed WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License
# for more details.

class SecurityHeadersMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        async def wrapped_send(message):
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                # Add security headers
                headers.extend([
# Refused to apply inline style because it violates the following Content Security Policy directive: "default-src 'self'". Either the 'unsafe-inline' keyword, a hash ('sha256-G7VxJAVCK/A442hTih1csBJhCXAmoaUO/rhj3qv07tQ='), or a nonce ('nonce-...') is required to enable inline execution. Note also that 'style-src' was not explicitly set, so 'default-src' is used as a fallback.
                    (b"Content-Security-Policy", b"default-src 'self'; script-src 'self'; object-src 'none';"),
                    (b"X-Content-Type-Options", b"nosniff"),
                    (b"X-Frame-Options", b"SAMEORIGIN"),
                    (b"X-XSS-Protection", b"1; mode=block"),
                    (b"Referrer-Policy", b"no-referrer-when-downgrade"),
                    (b"Permissions-Policy", b"geolocation=(), microphone=(), camera=()"),
                    # (b"Strict-Transport-Security", b"max-age=31536000; includeSubDomains"),
# Here are some additional headers that you might consider adding depending on your security needs:
# 
# X-Frame-Options: Prevents the site from being embedded in an iframe. The SAMEORIGIN value is commonly used, but you might want to use DENY if you don't want it embedded anywhere.
# Strict-Transport-Security (HSTS): Enforces HTTPS, ensuring that all requests are made over a secure connection. This is crucial for protecting against protocol downgrade attacks and cookie hijacking.
# Referrer-Policy: Controls how much referrer information is included with requests. no-referrer-when-downgrade is a common setting that provides a balance between security and usability.
# No Referrer on Downgrade: The browser will not send the Referer header if the request is made from a secure HTTPS page to a less secure HTTP page. This prevents leaking potentially sensitive information (like query parameters or path details) over an unencrypted connection.
# 
# Permissions-Policy: Allows you to control which browser features can be used on your site, such as geolocation or microphone access. Here they are all blocked.
                ])
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, wrapped_send)
