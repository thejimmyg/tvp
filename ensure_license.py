# Copyright (c) James Gardner 2024 All Rights Reserved
# This file is licensed under the GNU Lesser General Public License (LGPL) v3.0.
# You may obtain a copy of the license at http://www.gnu.org/licenses/lgpl-3.0.html.
# 
# This software is distributed WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License
# for more details.

import os
import fnmatch
import subprocess

# Define the original license text
license_text = """Copyright (c) James Gardner 2024 All Rights Reserved
This file is licensed under the GNU Lesser General Public License (LGPL) v3.0.
You may obtain a copy of the license at http://www.gnu.org/licenses/lgpl-3.0.html.

This software is distributed WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License
for more details."""

# Old license texts (if any) to be removed
old_license_texts = [
]

# Generate the header for each format from the license text
def generate_header(license_text, comment_style):
    if comment_style == "hash":
        return "\n".join([f"# {line}" for line in license_text.splitlines()]) + "\n\n"
    elif comment_style == "slash_star":
        return "/*\n" + "\n".join([f" * {line}" for line in license_text.splitlines()]) + "\n */\n\n"
    elif comment_style == "html_comment":
        return "<!--\n" + "\n".join([f" * {line}" for line in license_text.splitlines()]) + "\n -->\n\n"
    else:
        raise ValueError(f"Unknown comment style: {comment_style}")

# Generate old headers to remove, based on old license texts
def generate_old_headers(old_license_texts, comment_style):
    return [generate_header(old_license, comment_style) for old_license in old_license_texts]

# Define the license headers for different file types
headers = {
    ".py": generate_header(license_text, "hash"),
    "Dockerfile": generate_header(license_text, "hash"),
    ".css": generate_header(license_text, "slash_star"),
    ".md": generate_header(license_text, "html_comment"),
    ".dockerignore": generate_header(license_text, "hash"),
    ".zipignore": generate_header(license_text, "hash"),
    ".gitignore": generate_header(license_text, "hash"),
}

# Define old license headers for different file types (to be removed)
old_headers = {
    ".py": generate_old_headers(old_license_texts, "hash"),
    "Dockerfile": generate_old_headers(old_license_texts, "hash"),
    ".css": generate_old_headers(old_license_texts, "slash_star"),
    ".md": generate_old_headers(old_license_texts, "html_comment"),
    ".dockerignore": generate_old_headers(license_text, "hash"),
    ".zipignore": generate_old_headers(license_text, "hash"),
    ".gitignore": generate_old_headers(license_text, "hash"),
}

# Function to check if a file is binary
def is_binary(file_path):
    try:
        with open(file_path, 'rb') as f:
            chunk = f.read(1024)  # Read the first 1KB to check for binary data
            if b'\0' in chunk:  # Check for null bytes in the first 1KB
                return True
    except Exception as e:
        print(f"Error checking if file is binary: {file_path}: {e}")
    return False

# Use git to retrieve the ignored files
def get_gitignored_files():
    gitignored = set()
    try:
        result = subprocess.run(['git', 'ls-files', '--others', '--ignored', '--exclude-standard'],
                                stdout=subprocess.PIPE, text=True)
        gitignored = set(result.stdout.splitlines())
    except Exception as e:
        print(f"Error fetching gitignored files: {e}")
    return gitignored

# Check if the header is already present in the file
def has_header(file_path, header):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read(len(header))
            return header in content
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return False

# Remove old license headers from the file content
def remove_old_license(content, old_headers):
    for old_header in old_headers:
        if old_header in content:
            content = content.replace(old_header, '')
    return content

# Add header to the file if not present
def add_header(file_path, header, old_headers):
    try:
        with open(file_path, 'r+', encoding='utf-8') as f:
            content = f.read()

            # Remove any old license headers
            content = remove_old_license(content, old_headers)

            f.seek(0)
            f.write(header + content)
            f.truncate()  # Ensure the file is truncated in case the new content is shorter
            print(f"Header added to {file_path}")
    except Exception as e:
        print(f"Error writing to file {file_path}: {e}")

# Recursively process all files and track skipped files
def process_files(root_dir, gitignore_files):
    skipped_files = []
    for root, dirs, files in os.walk(root_dir):
        # Skip .git directory
        if '.git' in dirs:
            dirs.remove('.git')

        for file in files:
            file_path = os.path.join(root, file)

            # Skip gitignored files first
            if file_path[2:] in gitignore_files:
                skipped_files.append((file_path, "gitignored"))
                continue

            # Skip binary files
            if is_binary(file_path):
                skipped_files.append((file_path, "binary file"))
                continue

            # Determine the correct header based on file extension or name
            ext = os.path.splitext(file)[1]  # Get file extension
            header = headers.get(ext) or headers.get(file)
            old_header_list = old_headers.get(ext) or old_headers.get(file)

            # If the file is not supported by any header, skip it
            if not header:
                skipped_files.append((file_path, "unsupported file type"))
                continue

            # If the file already has the header, skip it
            if has_header(file_path, header):
                skipped_files.append((file_path, "header already exists"))
                continue

            # Add header to the file
            add_header(file_path, header, old_header_list)

    return skipped_files

# Main function to trigger the process
if __name__ == "__main__":
    gitignore_files = get_gitignored_files()
    skipped_files = process_files(".", gitignore_files)

    # Print the list of skipped files and why they were skipped
    print("\nSkipped Files:")
    for file_path, reason in skipped_files:
        print(f"{file_path} - {reason}")

