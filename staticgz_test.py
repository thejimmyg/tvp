# Copyright (c) James Gardner 2024 All Rights Reserved
# This file is licensed under the GNU Lesser General Public License (LGPL) v3.0.
# You may obtain a copy of the license at http://www.gnu.org/licenses/lgpl-3.0.html.
# 
# This software is distributed WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License
# for more details.

import unittest
import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, patch
from staticgz import StaticGzipMiddleware
import json
import gzip
from tempfile import TemporaryDirectory

# XXX might want a test to check that only the GET method actually tries to serve a static file.

class TestStaticGzipMiddleware(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.staticgz_dir = Path(self.tmp_dir.name) / "staticgz"
        self.staticgz_dir.mkdir(parents=True)
        self.statics_json_path = Path(self.tmp_dir.name) / "statics.json"


        # Setup a test gzipped file and corresponding JSON data
        self.gz_file_path = self.staticgz_dir / "test.txt"
        self.original_content = b"Hello, World! " * 1000
        with self.gz_file_path.open("wb") as f:
            f.write(gzip.compress(self.original_content))

        self.file_data = {
            "mtime": self.gz_file_path.stat().st_mtime,
            "size": len(b"Hello, World! " * 1000),
            "gzipped_size": self.gz_file_path.stat().st_size,
        }
        with self.statics_json_path.open("w") as f:
            json.dump({
                "test.txt": self.file_data,
            }, f)

        self.mock_app = AsyncMock()
        self.middleware = StaticGzipMiddleware(
            self.mock_app,
            staticgz_dir=str(self.staticgz_dir),
            statics_json_path=str(self.statics_json_path),
        )

    async def asyncTearDown(self):
        self.tmp_dir.cleanup()

    async def simulate_request(self, path, headers=None):
        headers = headers or []
        scope = {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": headers,
        }
        receive = AsyncMock()
        send = AsyncMock()
        await self.middleware(scope, receive, send)
        return send

    async def test_serve_gzipped_file(self):
        send = await self.simulate_request("/test.txt", headers=[(b"accept-encoding", b"gzip")])
        start_call = send.mock_calls[0]
        self.assertEqual(start_call[1][0]["status"], 200)
        self.assertIn((b"content-encoding", b"gzip"), start_call[1][0]["headers"])

    async def test_fallback_to_app(self):
        send = await self.simulate_request("/nonexistent.txt")
        self.mock_app.assert_called_once()

    async def test_etag_generation_and_304_response(self):
        # Calculate expected ETag based on mtime and size
        expected_etag = hashlib.md5(f"{self.file_data['mtime']}{self.file_data['size']}".encode()).hexdigest()
        expected_weak_etag = f'W/"{expected_etag}"'

        # First request to get the file and its ETag
        send = await self.simulate_request("/test.txt", headers=[(b"accept-encoding", b"gzip")])
        start_call = send.mock_calls[0]
        headers = start_call[1][0]["headers"]

        etag_header = [h for h in headers if h[0] == b"etag"]
        self.assertEqual(len(etag_header), 1, "ETag header should be present in the response")
        etag = etag_header[0][1]

        # Assert that the generated ETag matches the expected ETag
        self.assertEqual(etag.decode(), expected_weak_etag, "Generated ETag does not match expected ETag")

        # Second request with If-None-Match header using the ETag
        send = await self.simulate_request("/test.txt", headers=[(b"accept-encoding", b"gzip"), (b"if-none-match", etag)])
        start_call = send.mock_calls[0]

        # Check that the response status is 304 and that no body is sent
        self.assertEqual(start_call[1][0]["status"], 304)
        self.assertIn((b"etag", etag), start_call[1][0]["headers"])

if __name__ == "__main__":
    unittest.main()

