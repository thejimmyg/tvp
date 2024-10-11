# Copyright (c) James Gardner 2024 All Rights Reserved
# This file is licensed under the GNU Lesser General Public License (LGPL) v3.0.
# You may obtain a copy of the license at http://www.gnu.org/licenses/lgpl-3.0.html.
# 
# This software is distributed WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License
# for more details.

import os
import mimetypes
import argparse
import json

def get_extension_mimetype_mapping(directory):
    # Dictionary to hold the extension -> mime type mapping
    ext_to_mime = {}

    # Walk through the directory and its subdirectories
    for root, dirs, files in os.walk(directory):
        for file in files:
            # Get the file extension in lowercase
            file_ext = os.path.splitext(file)[1].lower()

            # Guess the MIME type using mimetypes
            mime_type, _ = mimetypes.guess_type(file)

            # If mime_type is None, we set it to "application/octet-stream"
            if mime_type is None:
                mime_type = "application/octet-stream"

            # Update the dictionary
            if file_ext not in ext_to_mime:
                ext_to_mime[file_ext] = mime_type
            else:
                # If the extension exists, ensure no conflicts in mime types
                if ext_to_mime[file_ext] != mime_type:
                    print(f"Warning: Extension {file_ext} maps to multiple MIME types ({ext_to_mime[file_ext]} and {mime_type})")

    return ext_to_mime

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Recursively walk a directory and map file extensions to MIME types.')
    parser.add_argument('www', type=str, help='The www directory to walk through for discovering mime types')

    # Parse the arguments
    args = parser.parse_args()

    # Get the mapping of file extensions to MIME types
    ext_to_mime = get_extension_mimetype_mapping(args.www)

    # Output the mapping as a JSON dictionary
    print(json.dumps(ext_to_mime, indent=4))

if __name__ == '__main__':
    main()
