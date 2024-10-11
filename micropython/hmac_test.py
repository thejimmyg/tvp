# Copyright (c) James Gardner 2024 All Rights Reserved
# This file is licensed under the GNU Lesser General Public License (LGPL) v3.0.
# You may obtain a copy of the license at http://www.gnu.org/licenses/lgpl-3.0.html.
# 
# This software is distributed WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License
# for more details.

import hmac
import hashlib

# Example key and message
secret = b'secret_key'
message = b'This is a message'
expected_sig = '55ac7e647c55ef0552d991f79aa2c7037c6585c0c98aa4c1ac206b1933fc030e'

# Generate HMAC signature using SHA-256
sig = hmac.new(secret, message, hashlib.sha256).hexdigest()
print("Generated signature:", sig)

# Compare signatures
if hmac.compare_digest(sig, expected_sig):
    print("Signatures match!")
else:
    print("Signatures do not match!")
