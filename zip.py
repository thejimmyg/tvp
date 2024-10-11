# Copyright (c) James Gardner 2024 All Rights Reserved
# This file is licensed under the GNU Lesser General Public License (LGPL) v3.0.
# You may obtain a copy of the license at http://www.gnu.org/licenses/lgpl-3.0.html.
# 
# This software is distributed WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License
# for more details.

import glob
import os
import sys
import time
import zipfile

def load_zipignore_patterns(zipignore_file):
    patterns = []
    if os.path.exists(zipignore_file):
        with open(zipignore_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    patterns.append(line)
    return patterns

def should_ignore(file_path, patterns):
    """Check if the file or directory matches any of the .zipignore patterns using glob."""
    for pattern in patterns:
        # Convert .zipignore patterns into a glob-friendly pattern
        if glob.fnmatch.fnmatch(file_path, pattern) or glob.fnmatch.fnmatch(os.path.basename(file_path), pattern):
            return True
    return False

def zip_dir(zf, dir_to_zip, ignore_patterns=[]):
    for root, dirs, files in os.walk(dir_to_zip):
        # Remove ignored directories based on .zipignore
        dirs[:] = [d for d in dirs if not should_ignore(os.path.relpath(os.path.join(root, d), dir_to_zip), ignore_patterns)]
        for file in files:
            abs_file = os.path.join(root, file)
            arcname = os.path.relpath(abs_file, dir_to_zip)
            # Skip files that match .zipignore patterns
            if not should_ignore(abs_file, ignore_patterns):
                stat = os.stat(abs_file)  # Use abs_file here
                zip_info = zipfile.ZipInfo(arcname)
                mod_time = time.localtime(stat.st_mtime)
                zip_info.date_time = mod_time[:6]  # first six elements: (year, month, day, hour, minute, second)
                with open(abs_file, 'rb') as file:
                    if arcname.startswith('wwwgz/'):
                        print('    STORED', arcname)
                        zf.writestr(zip_info, file.read(), compress_type=zipfile.ZIP_STORED)
                    else:
                        print('COMPRESSED', arcname)
                        zf.writestr(zip_info, file.read(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

if __name__ == '__main__':
    import json
    from mimetypes_cli import get_extension_mimetype_mapping
    from staticgz_cli import populate_staticgz

    ext_to_mime = get_extension_mimetype_mapping('www')
    with open('mimetypes.json', 'wb') as fp:
        fp.write(json.dumps(ext_to_mime, indent=4).encode('utf8'))

    populate_staticgz('www', 'wwwgz', 'wwwgz.json')

    # Load .zipignore patterns
    zipignore_file = sys.argv[1]
    ignore_patterns = load_zipignore_patterns(zipignore_file)

    # Create the zip file
    zip_filename = sys.argv[2]
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zip_dir(zf, '.', ignore_patterns=ignore_patterns)
