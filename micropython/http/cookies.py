# Copyright (c) James Gardner 2024 All Rights Reserved
# This file is licensed under the GNU Lesser General Public License (LGPL) v3.0.
# You may obtain a copy of the license at http://www.gnu.org/licenses/lgpl-3.0.html.
# 
# This software is distributed WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License
# for more details.

class SimpleCookie:
    def __init__(self, cookie_header=None):
        self.cookies = {}
        if cookie_header:
            self.load(cookie_header)

    def load(self, cookie_header):
        """Parses the cookie header."""
        cookies = cookie_header.split(';')
        for cookie in cookies:
            if '=' in cookie:
                key, value = cookie.split('=', 1)
                self.cookies[key.strip()] = Morsel(value.strip())

    def get(self, key, default=None):
        """Gets a cookie by key, returns default if not found."""
        return self.cookies.get(key, default)

    def __getitem__(self, key):
        """Gets a cookie by key (like dictionary access)."""
        return self.cookies.get(key, Morsel())

    def __setitem__(self, key, value):
        """Sets a cookie value."""
        morsel = Morsel(value)
        self.cookies[key] = morsel

    def items(self):
        """Returns the items of the cookie dictionary."""
        return self.cookies.items()

    def output(self, header='', sep='; '):
        """Generates a string suitable for the Cookie HTTP header."""
        return sep.join([f"{key}={morsel.output()}" for key, morsel in self.cookies.items()])

class Morsel:
    def __init__(self, value=''):
        self.value = value
        self.attributes = {
            'path': None,
            'httponly': False,
            'secure': False,
            'samesite': None,
            'max-age': None
        }

    def __getitem__(self, key):
        """Gets an attribute value."""
        return self.attributes.get(key)

    def __setitem__(self, key, value):
        """Sets an attribute value."""
        if key in self.attributes:
            self.attributes[key] = value

    def output(self):
        """Returns the value with attributes for the cookie header."""
        attrs = []
        if self.attributes['path']:
            attrs.append(f'Path={self.attributes["path"]}')
        if self.attributes['httponly']:
            attrs.append('HttpOnly')
        if self.attributes['secure']:
            attrs.append('Secure')
        if self.attributes['samesite']:
            attrs.append(f'SameSite={self.attributes["samesite"]}')
        if self.attributes['max-age'] is not None:
            attrs.append(f'Max-Age={self.attributes["max-age"]}')
        return f'{self.value}; ' + '; '.join(attrs).strip('; ')


if __name__ == '__main__':
    # Sample usage for compatibility
    def parse_cookies(headers):
        """Parses cookies from headers."""
        # Manually search for the 'cookie' header to avoid using 'next()'
        cookie_header = None
        for key, value in headers:
            if key == b'cookie':
                cookie_header = value
                break
        if cookie_header:
            return SimpleCookie(cookie_header.decode('latin1'))
        return SimpleCookie()
    
    # Simulated usage example:
    headers = [(b'cookie', b'csrf_token_bundle=abc123')]
    cookies = parse_cookies(headers)
    print(cookies.get('csrf_token_bundle').value)  # Output should be 'abc123'
    
    # Setting cookies
    cookie = SimpleCookie()
    cookie['csrf_token_bundle'] = 'new_token_value'
    cookie['csrf_token_bundle']['path'] = '/'
    cookie['csrf_token_bundle']['httponly'] = True
    cookie['csrf_token_bundle']['secure'] = True
    cookie['csrf_token_bundle']['samesite'] = 'Strict'
    cookie['csrf_token_bundle']['max-age'] = 3600
    new_cookie_header = cookie.output(header='', sep='').encode('utf-8').strip()
    print(new_cookie_header)
