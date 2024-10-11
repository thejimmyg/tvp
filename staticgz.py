# Copyright (c) James Gardner 2024 All Rights Reserved
# This file is licensed under the GNU Lesser General Public License (LGPL) v3.0.
# You may obtain a copy of the license at http://www.gnu.org/licenses/lgpl-3.0.html.
# 
# This software is distributed WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License
# for more details.

"""
The etag is always formed from the size and mtime of the non-gzip file.

The Accept-Content request header is ignored, it is assumed the client can cope with gzip.

Security Review of the Code
Path Traversal and Directory Security

Path Resolution:
The file_path is resolved using file_path = (self.public / path).resolve(). This ensures that the resolved path is absolute.
The critical check is if not file_path.is_relative_to(self.public):. This ensures that the resolved file_path is within the bounds of the self.public directory. This prevents directory traversal attacks effectively.
Handling of publicgz:
The gzipped files are similarly handled by resolving publicgz_path when self.publicgz is provided. The security check remains robust as the middleware won't serve files from outside the intended directories.
ETag Handling

ETag Generation:
ETags are generated using hashlib.md5(f"{file_path.stat().st_mtime}{file_path.stat().st_size}".encode()).hexdigest(). This method correctly bases the ETag on the file's modification time (st_mtime) and size (st_size), ensuring that any change in the file will produce a new ETag.
Consistency for Gzipped Files: The current implementation uses different paths (public vs. publicgz) to generate the ETag. However, the ETag should be consistent for both the gzipped and non-gzipped versions. To fix this, the ETag should be calculated based on the original (non-gzipped) file's st_mtime and st_size
"""

import hashlib
import mimetypes
import os
import json
import urllib.parse
from pathlib import Path

from static import is_valid_etag
import fileio

class StaticGzipMiddleware:
    def __init__(self, app, staticgz_dir, statics_json_path):
        self.app = app
        self.staticgz = Path(staticgz_dir) #.resolve()
        self.statics_json_path = Path(statics_json_path) #.resolve()
        self.statics_data = json.loads(fileio.read(str(self.statics_json_path)).decode('utf8'))

    async def __call__(self, scope, receive, send):
        print(f"Path: {scope['path']}, Headers: {dict(scope['headers'])}")
        if scope["type"] != "http" or scope["method"] != 'GET':
            return await self.app(scope, receive, send)
    
        path = Path(urllib.parse.unquote(scope["path"]).lstrip("/"))
    
        file_data = self.statics_data.get(str(path))
        if file_data and 'gzipped_size' in file_data:
            accept_encoding = dict(scope['headers']).get(b'accept-encoding', b'').decode('utf-8')
            if 'gzip' in accept_encoding:
                gz_file_path = self.staticgz / path
                exists, mtime, size = fileio.stat(str(gz_file_path))
                if exists:
                    print(file_data, str(path), repr(accept_encoding), gz_file_path)
                    if_none_match = dict(scope['headers']).get(b'if-none-match', b'').decode('utf-8')
                    await self.serve_gzipped_file(gz_file_path, file_data, if_none_match, send)
                    return
    
        await self.app(scope, receive, send)

    async def serve_gzipped_file(self, gz_file_path, file_data, if_none_match, send):
        etag = hashlib.md5(f"{file_data['mtime']}{file_data['size']}".encode()).hexdigest()
        weak_etag = f'W/"{etag}"'
        mime_type, _ = mimetypes.guess_type(str(gz_file_path))
        mime_type = mime_type or "application/octet-stream"
    
        # Compare the If-None-Match header with the generated ETag
        if if_none_match and is_valid_etag(weak_etag, if_none_match):
            print(f"ETag matches: {if_none_match}")
            await send({
                "type": "http.response.start",
                "status": 304,
                "headers": [
                    (b"etag", weak_etag.encode()),
                ],
            })
            await send({"type": "http.response.body", "body": b""})
            return
    
        response_headers = [
            (b"content-length", str(file_data["gzipped_size"]).encode()),
            (b"content-type", mime_type.encode()),
            (b"etag", weak_etag.encode()),
            (b"content-encoding", b"gzip"),
        ]
    
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": response_headers,
        })
    
        # XXX Should use chunking really.
        # with gz_file_path.open("rb") as file:
        #     while chunk := file.read(8192):
        #         await send({"type": "http.response.body", "body": chunk, "more_body": True})
        # await send({"type": "http.response.body", "body": b"", "more_body": False})
        await send({"type": "http.response.body", "body": fileio.read(str(gz_file_path)), "more_body": False})
