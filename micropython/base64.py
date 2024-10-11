# Copyright (c) James Gardner 2024 All Rights Reserved
# This file is licensed under the GNU Lesser General Public License (LGPL) v3.0.
# You may obtain a copy of the license at http://www.gnu.org/licenses/lgpl-3.0.html.
# 
# This software is distributed WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License
# for more details.

from binascii import a2b_base64 as b64decode
from binascii import b2a_base64

def urlsafe_b64encode_without_padding(data):
    # Base64 encode the data
    b64 = b2a_base64(data).rstrip(b'\n')

    # Convert to string, replace URL-unsafe characters (+, /) with (-, _)
    url_safe_b64 = b64.replace(b'+', b'-').replace(b'/', b'_')

    # Remove padding ('=') and return as UTF-8 string
    return url_safe_b64.rstrip(b'=').decode('utf-8')
