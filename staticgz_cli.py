# Copyright (c) James Gardner 2024 All Rights Reserved
# This file is licensed under the GNU Lesser General Public License (LGPL) v3.0.
# You may obtain a copy of the license at http://www.gnu.org/licenses/lgpl-3.0.html.
# 
# This software is distributed WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License
# for more details.

import gzip
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import argparse

def populate_staticgz(static_dir, staticgz_dir, statics_json_path):
    static_dir = Path(static_dir).resolve()
    staticgz_dir = Path(staticgz_dir).resolve()
    statics_json_path = Path(statics_json_path).resolve()

    if not statics_json_path.exists():
        statics_data = {}
    else:
        with statics_json_path.open("r") as f:
            statics_data = json.load(f)

    # Remove any files in staticgz not in static
    for gz_file in staticgz_dir.rglob('*'):
        corresponding_static_file = static_dir / gz_file.relative_to(staticgz_dir)
        if not corresponding_static_file.exists():
            gz_file.unlink()

    # Process all files in static
    for static_file in static_dir.rglob('*'):
        if static_file.is_dir():
            continue

        rel_path = static_file.relative_to(static_dir)
        gz_file = staticgz_dir / rel_path

        if str(rel_path) in statics_data:
            saved_mtime = statics_data[str(rel_path)]["mtime"]
            current_mtime = int(static_file.stat().st_mtime)

            # If mtime is different or gz_file doesn't exist, reprocess
            if saved_mtime != current_mtime or not gz_file.exists():
                statics_data.pop(str(rel_path))
                gz_file.unlink(missing_ok=True)
            else:
                continue

        # Compress and store the file if gzipping reduces size
        with static_file.open("rb") as f_in:
            content = f_in.read()
        gz_content = gzip.compress(content)

        if len(gz_content) < len(content):
            gz_file.parent.mkdir(parents=True, exist_ok=True)
            with gz_file.open("wb") as f_out:
                f_out.write(gz_content)

            statics_data[str(rel_path)] = {
                "mtime": int(static_file.stat().st_mtime),
                "size": len(content),
                "gzipped_size": len(gz_content),
            }
        # else:
        #     statics_data[str(rel_path)] = {
        #         "mtime": static_file.stat().st_mtime,
        #         "size": len(content),
        #         "gzipped_size": len(content),  # Mark it as not useful for gzipping
        #     }
    to_delete = []
    for relpath in statics_data:
        if not os.path.exists(os.path.join(static_dir, str(relpath))):
            to_delete.append(relpath)
    for k in to_delete:
        del statics_data[k]

    # Save the statics.json
    with statics_json_path.open("w") as f:
        json.dump(statics_data, f, indent=4)

staticgz_parser = argparse.ArgumentParser(description="Populate staticgz directory and statics.json file.")
staticgz_parser.add_argument("static_dir", help="Path to the static directory.")
staticgz_parser.add_argument("staticgz_dir", help="Path to the staticgz directory.")
staticgz_parser.add_argument("statics_json_path", help="Path to save the statics.json file.")

if __name__ == "__main__":
    args = staticgz_parser.parse_args()
    populate_staticgz(args.static_dir, args.staticgz_dir, args.statics_json_path)
