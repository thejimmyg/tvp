# Copyright (c) James Gardner 2024 All Rights Reserved
# This file is licensed under the GNU Lesser General Public License (LGPL) v3.0.
# You may obtain a copy of the license at http://www.gnu.org/licenses/lgpl-3.0.html.
# 
# This software is distributed WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License
# for more details.

# First stage: use a full-featured Python image to install dependencies
FROM python:3-slim AS builder

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY . .

# Install dependencies to a custom location (/deps)
RUN mkdir /deps
# RUN pip install --no-cache-dir --target=/deps -r requirements.txt

RUN python3 mimetypes_cli.py www > mimetypes.json
RUN python3 staticgz_cli.py www wwwgz wwwgz.json

# Second stage: use distroless as the runtime
FROM gcr.io/distroless/python3:nonroot

# Set the working directory
WORKDIR /app

# Copy the installed dependencies from the first stage to /deps
COPY --from=builder /deps /deps

# Copy the rest of the application code
COPY . .

# Set PYTHONPATH to include /deps so Python can find the installed packages
ENV PYTHONPATH=/deps

# Expose the port
EXPOSE 9000

# Command to run the app
CMD ["__main__.py", "0.0.0.0:9000", "1", "app:application"]
