# Copyright (c) James Gardner 2024 All Rights Reserved
# This file is licensed under the GNU Lesser General Public License (LGPL) v3.0.
# You may obtain a copy of the license at http://www.gnu.org/licenses/lgpl-3.0.html.
# 
# This software is distributed WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License
# for more details.

import sys
if sys.implementation.name == 'micropython':
    sys.path.append('micropython')

import fileio
print(fileio.stat('www/nav.css'))

if __name__ == "__main__":
    import serve
    import app

    serve.main(app.application, address=sys.argv[1], num_workers=int(sys.argv[2]))
