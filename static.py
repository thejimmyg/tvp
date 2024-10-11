# Copyright (c) James Gardner 2024 All Rights Reserved
# This file is licensed under the GNU Lesser General Public License (LGPL) v3.0.
# You may obtain a copy of the license at http://www.gnu.org/licenses/lgpl-3.0.html.
# 
# This software is distributed WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License
# for more details.

import hashlib
from pathlib import Path
import urllib.parse
import os
import json

import fileio

def is_valid_etag(weak_etag, if_none_matched):
    weak_etag = weak_etag.strip()
    if_none_matched = [etag.strip() for etag in if_none_matched.split(",")]
    weak_etag_no_prefix = weak_etag[2:] if weak_etag.startswith("W/") else weak_etag
    for etag in if_none_matched:
        if (
            etag == weak_etag
            or etag == weak_etag_no_prefix
            or etag == f"W/{weak_etag_no_prefix}"
        ):
            return True
    return False

class StaticFilesMiddleware:
    def __init__(self, app, public_dir, mimetypes_file):
        self.app = app
        self.public = Path(public_dir) #//.resolve()
        self.mimetypes = json.loads(fileio.read(mimetypes_file).decode('utf8')) # Prepared with mimetypes_cli.py

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != 'GET':
            return await self.app(scope, receive, send)
        await self.handle_static_file(scope, receive, send)

    async def handle_static_file(self, scope, receive, send):
        path = Path(urllib.parse.unquote(scope["path"]).lstrip("/"))
        headers = {key.decode().lower(): value for key, value in scope["headers"]}
        if_none_match = headers.get("if-none-match")

        # Combine with the public directory and resolve the full path
        file_path = self.public / path # // .resolve()

        # Security check to prevent serving files outside the public directory
        if not file_path.is_relative_to(self.public):
            await send({
                "type": "http.response.start",
                "status": 400,
                "headers": [(b"content-length", b"11")],
            })
            await send({"type": "http.response.body", "body": b"Bad Request"})
            return

        if file_path.is_dir():
            if (file_path / "index.html").is_file():
                location = f"{path}/index.html"
                await send({
                    "type": "http.response.start",
                    "status": 302,
                    "headers": [
                        (b"location", location.encode()),
                        (b"content-length", b"0")
                    ],
                })
                await send({"type": "http.response.body", "body": b""})
                return
            else:
                await self.app(scope, receive, send)
                return

        exists, mtime, size = fileio.stat(str(file_path))
        if not exists:
            return await self.app(scope, receive, send)
           
        etag = hashlib.md5(f"{mtime}{size}".encode()).hexdigest()
        weak_etag = f'W/"{etag}"'
        mime_type = self.mimetypes.get(os.path.splitext(file_path)[1].lower(), "application/octet-stream")

        if if_none_match and is_valid_etag(weak_etag, if_none_match.decode("utf8")):
            print('304 for', path)
            await send({
                "type": "http.response.start",
                "status": 304,
                "headers": [
                    (b"etag", weak_etag.encode())
                ],
            })
            await send({"type": "http.response.body", "body": b""})
            return

        response_headers = [
            (b"content-length", str(size).encode()),
            (b"content-type", mime_type.encode()),
            (b"etag", weak_etag.encode()),
        ]

        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": response_headers,
        })

        print('200 for', path)
        # XXX Should use chunking really.
        # with file_path.open("rb") as file:
        #     while True:
        #         chunk = file.read(8192)
        #         if not chunk:
        #             break
        #        await send({"type": "http.response.body", "body": chunk, "more_body": True})
        await send({"type": "http.response.body", "body": fileio.read(str(file_path)), "more_body": False})

