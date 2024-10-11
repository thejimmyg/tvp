# Copyright (c) James Gardner 2024 All Rights Reserved
# This file is licensed under the GNU Lesser General Public License (LGPL) v3.0.
# You may obtain a copy of the license at http://www.gnu.org/licenses/lgpl-3.0.html.
# 
# This software is distributed WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License
# for more details.

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from staticgz_cli import populate_staticgz  # Adjust import as necessary
import json
import gzip
import time

class TestPopulateStaticgz(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = TemporaryDirectory()
        self.static_dir = Path(self.tmp_dir.name) / "static"
        self.staticgz_dir = Path(self.tmp_dir.name) / "staticgz"
        self.statics_json_path = Path(self.tmp_dir.name) / "statics.json"

        self.static_dir.mkdir(parents=True)
        self.staticgz_dir.mkdir(parents=True)

        # Create test files
        self.file_path = self.static_dir / "test.txt"
        self.original_content = b"Hello, World! " * 1000
        with self.file_path.open("wb") as f:
            f.write(self.original_content)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_populate_staticgz(self):
        populate_staticgz(self.static_dir, self.staticgz_dir, self.statics_json_path)
        gz_file_path = self.staticgz_dir / "test.txt"

        # Check if the gzipped file exists
        self.assertTrue(gz_file_path.exists(), "Gzipped file should be created")

        # Verify the gzipped content by decompressing it and comparing with original content
        with gzip.open(gz_file_path, "rb") as gz_file:
            decompressed_content = gz_file.read()
        self.assertEqual(decompressed_content, self.original_content, "Decompressed content should match the original")

        # Verify the contents of statics.json
        with self.statics_json_path.open("r") as f:
            statics_data = json.load(f)
        
        # Ensure the file entry is in statics_data
        self.assertIn("test.txt", statics_data, "statics_data should contain an entry for 'test.txt'")
        
        # Check the recorded mtime, size, and gzipped size
        recorded_data = statics_data["test.txt"]
        self.assertEqual(recorded_data["size"], len(self.original_content), "File size should be recorded correctly")
        self.assertEqual(recorded_data["gzipped_size"], gz_file_path.stat().st_size, "Gzipped size should be recorded correctly")
        self.assertEqual(recorded_data["mtime"], self.file_path.stat().st_mtime, "Modification time should be recorded correctly")

    def test_no_recompression_if_unchanged(self):
        # First populate run
        populate_staticgz(self.static_dir, self.staticgz_dir, self.statics_json_path)
        gz_file_path = self.staticgz_dir / "test.txt"

        initial_mtime = gz_file_path.stat().st_mtime
        initial_size = gz_file_path.stat().st_size

        # Wait to ensure mtime resolution is surpassed
        time.sleep(1)

        # Second populate run (no changes to source file)
        populate_staticgz(self.static_dir, self.staticgz_dir, self.statics_json_path)

        self.assertEqual(initial_mtime, gz_file_path.stat().st_mtime, "Gzipped file mtime should not change if the source file hasn't changed")
        self.assertEqual(initial_size, gz_file_path.stat().st_size, "Gzipped file size should remain the same if the source file hasn't changed")

        # Modify the source file and re-run populate
        with self.file_path.open("ab") as f:
            f.write(b" Additional content.")

        # Third populate run (after modifying the source file)
        populate_staticgz(self.static_dir, self.staticgz_dir, self.statics_json_path)

        self.assertNotEqual(initial_mtime, gz_file_path.stat().st_mtime, "Gzipped file mtime should change if the source file has changed")
        self.assertNotEqual(initial_size, gz_file_path.stat().st_size, "Gzipped file size should change if the source file has changed")

if __name__ == "__main__":
    unittest.main()
