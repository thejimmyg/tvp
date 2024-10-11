# Copyright (c) James Gardner 2024 All Rights Reserved
# This file is licensed under the GNU Lesser General Public License (LGPL) v3.0.
# You may obtain a copy of the license at http://www.gnu.org/licenses/lgpl-3.0.html.
# 
# This software is distributed WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License
# for more details.

import sys
import os
import time
import zipfile

root = '/'.join(__file__.replace('\\', '/').split('/')[:-1])

if root.endswith('.zip'):
    z = zipfile.ZipFile(root, 'r')

    def read(file_path):
        file_full_path = '/'.join([root, file_path])
        with z.open(file_path) as f:
            return f.read()

    def stat(file_path):
        try:
            file_info = z.getinfo(file_path)
        except KeyError:
            return False, None, None
        modified_time = time.mktime(file_info.date_time + (0, 0, -1))  # Convert to epoch
        file_size = file_info.file_size  # Uncompressed file size
        return True, int(modified_time), file_size
else:
    def read(file_path):
        file_full_path = '/'.join([root, file_path])
        with open(file_full_path, 'rb') as f:
            return f.read()

    def stat(file_path):
        file_full_path = '/'.join([root, file_path])
        try:
            file_info = os.stat(file_full_path)
            modified_time = file_info.st_mtime  # Time of last modification (epoch seconds)
        except FileNotFoundError:
            return False, None, None
        file_size = file_info.st_size       # Uncompressed file size
        return True, int(modified_time), file_size
