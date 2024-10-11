# Copyright (c) James Gardner 2024 All Rights Reserved
# This file is licensed under the GNU Lesser General Public License (LGPL) v3.0.
# You may obtain a copy of the license at http://www.gnu.org/licenses/lgpl-3.0.html.
# 
# This software is distributed WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License
# for more details.

import hashlib

# Constants
BLOCK_SIZE = 64  # Block size for SHA-256

class HMAC:
    def __init__(self, key, msg=None, digestmod=hashlib.sha256):
        assert digestmod == hashlib.sha256
        self.digestmod = digestmod
        self.block_size = BLOCK_SIZE

        # If the key is longer than the block size, hash it
        if len(key) > self.block_size:
            key = digestmod(key).digest()

        # If the key is shorter than the block size, pad it with zeros manually
        if len(key) < self.block_size:
            key = key + b'\x00' * (self.block_size - len(key))

        # Create inner and outer paddings
        self.ipad = bytes((x ^ 0x36) for x in key)
        self.opad = bytes((x ^ 0x5c) for x in key)

        # Start inner hash
        self.inner = self.digestmod()
        self.inner.update(self.ipad)

        if msg is not None:
            self.update(msg)

    def update(self, msg):
        """Updates the HMAC object with more message data."""
        self.inner.update(msg)

    def digest(self):
        """Returns the HMAC hash as bytes."""
        # Finalize the inner hash
        inner_hash = self.inner.digest()

        # Perform outer hash
        outer = self.digestmod()
        outer.update(self.opad)
        outer.update(inner_hash)

        return outer.digest()

    def hexdigest(self):
        """Returns the HMAC hash as a hexadecimal string."""
        return self.digest().hex()


def new(key, msg=None, digestmod=hashlib.sha256):
    """Creates a new HMAC object."""
    return HMAC(key, msg, digestmod)


def compare_digest(a, b):
    """Compares two digests in constant time to prevent timing attacks."""
    if isinstance(a, str):
        a = a.encode('utf-8')
    if isinstance(b, str):
        b = b.encode('utf-8')

    # Ensure both are the same length
    if len(a) != len(b):
        return False

    # Perform comparison in constant time
    result = 0
    for x, y in zip(a, b):
        result |= x ^ y

    return result == 0
