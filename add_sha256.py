#!/usr/bin/env python3
"""
Script to add SHA256 checksums to all EXTENSION files.
This script will:
1. Find all EXTENSION files
2. Parse their source URLs
3. Download the files and calculate SHA256 checksums
4. Update the EXTENSION files with sha256sums fields
"""

import os
import sys
import re
import hashlib
import urllib.request
import urllib.parse
import tempfile
import shlex
from pathlib import Path


def substitute_variables(value, variables):
    """Substitute variables in the format ${var} with their corresponding values"""
    pattern = re.compile(r"\$\{([^}]+)\}")
    
    def replace(match):
        var_name = match.group(1)
        return variables.get(var_name, match.group(0))
    
    return pattern.sub(replace, value)


def parse_extension_file(filepath):
    """Parse an EXTENSION file and return a dictionary of its contents"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Simple parsing - extract key=value pairs and arrays
    result = {}
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
            
        # Handle function definitions - skip them
        if line.endswith('() {') or 'package()' in line:
            break
            
        # Split on first = only
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip()
        
        # Handle arrays
        if value.startswith('(') and value.endswith(')'):
            # Parse array values
            array_content = value[1:-1].strip()
            if array_content:
                # Use shlex to properly parse quoted strings
                try:
                    lexer = shlex.shlex(array_content, posix=True)
                    lexer.whitespace_split = True
                    lexer.commenters = ''
                    result[key] = list(lexer)
                except:
                    # Fallback to simple split
                    result[key] = [item.strip().strip('"\'') for item in array_content.split()]
            else:
                result[key] = []
        else:
            # Remove quotes
            value = value.strip('"\'')
            result[key] = value
    
    # Substitute variables
    for k, v in result.items():
        if isinstance(v, list):
            result[k] = [substitute_variables(item, result) for item in v]
        else:
            result[k] = substitute_variables(v, result)
    
    return result


def calculate_sha256(url, temp_dir):
    """Download a file and calculate its SHA256 checksum"""
    print(f"Downloading {url}...")
    
    try:
        # Parse the URL to get filename
        parsed_url = urllib.parse.urlparse(url)
        filename = os.path.basename(parsed_url.path)
        if not filename:
            filename = "download"
        
        temp_file = os.path.join(temp_dir, filename)
        
        # Download the file
        urllib.request.urlretrieve(url, temp_file)
        
        # Calculate SHA256
        sha256_hash = hashlib.sha256()
        with open(temp_file, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        checksum = sha256_hash.hexdigest()
        print(f"SHA256: {checksum}")
        
        # Clean up
        os.remove(temp_file)
        
        return checksum
        
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return None


def update_extension_file(filepath, sha256_data):
    """Update an EXTENSION file with SHA256 checksums"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find where to insert sha256sums
    insert_index = None
    package_start = None
    
    for i, line in enumerate(lines):
        if line.strip().startswith('md5sums'):
            insert_index = i + 1
        elif line.strip().startswith('package()') or line.strip().endswith('() {'):
            package_start = i
            break
    
    if insert_index is None and package_start is not None:
        insert_index = package_start
    elif insert_index is None:
        insert_index = len(lines)
    
    # Prepare sha256sums lines
    new_lines = []
    for key, checksums in sha256_data.items():
        if len(checksums) == 1:
            new_lines.append(f'{key}=("{checksums[0]}")\n')
        else:
            checksum_str = ' '.join(f'"{checksum}"' for checksum in checksums)
            new_lines.append(f'{key}=({checksum_str})\n')
    
    # Insert the new lines
    lines[insert_index:insert_index] = new_lines
    
    # Write back to file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(lines)


def process_extension_file(filepath, force_update=False):
    """Process a single EXTENSION file"""
    print(f"\nProcessing {filepath}")

    try:
        data = parse_extension_file(filepath)

        # Find source URLs
        source_fields = {}
        for key, value in data.items():
            if key.startswith('source'):
                source_fields[key] = value if isinstance(value, list) else [value]

        if not source_fields:
            print("No source URLs found, skipping...")
            return True

        # Check which sha256sums fields are missing
        missing_sha256_fields = []
        existing_sha256_fields = []

        for source_key in source_fields.keys():
            sha256_key = source_key.replace('source', 'sha256sums')
            if sha256_key in data and not force_update:
                existing_sha256_fields.append(sha256_key)
                print(f"SHA256 checksum already exists for {source_key}")
            else:
                missing_sha256_fields.append((source_key, sha256_key))

        if not missing_sha256_fields and not force_update:
            print("All SHA256 checksums already exist, skipping...")
            return True

        if existing_sha256_fields and not force_update:
            print(f"Processing only missing SHA256 checksums: {[pair[1] for pair in missing_sha256_fields]}")
        
        # Calculate SHA256 for missing fields only
        sha256_data = {}
        with tempfile.TemporaryDirectory() as temp_dir:
            for source_key, sha256_key in missing_sha256_fields:
                urls = source_fields[source_key]
                checksums = []

                for url_spec in urls:
                    # Extract actual URL (format: "filename::url")
                    if '::' in url_spec:
                        _, url = url_spec.split('::', 1)
                    else:
                        url = url_spec

                    checksum = calculate_sha256(url, temp_dir)
                    if checksum:
                        checksums.append(checksum)
                    else:
                        print(f"Failed to calculate checksum for {url}")
                        return False

                sha256_data[sha256_key] = checksums

        if not sha256_data:
            print("No new SHA256 checksums to add")
            return True
        
        # Update the file
        update_extension_file(filepath, sha256_data)
        print(f"Successfully updated {filepath}")
        return True
        
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False


def find_extension_files(root_dir):
    """Find all EXTENSION files in the directory tree"""
    extension_files = []
    for root, dirs, files in os.walk(root_dir):
        if 'EXTENSION' in files:
            extension_files.append(os.path.join(root, 'EXTENSION'))
    return extension_files


def generate_metainfo_json(extension_dir):
    """Generate metainfo.json for a directory containing an EXTENSION file"""
    extension_file = os.path.join(extension_dir, 'EXTENSION')
    metainfo_file = os.path.join(extension_dir, 'metainfo.json')

    if not os.path.exists(extension_file):
        return False

    try:
        # Use extract_meta.py to generate JSON
        import subprocess
        import json

        # Get the directory of this script to find extract_meta.py
        script_dir = os.path.dirname(os.path.abspath(__file__))
        extract_meta_path = os.path.join(script_dir, 'extract_meta.py')

        if not os.path.exists(extract_meta_path):
            print(f"extract_meta.py not found at {extract_meta_path}")
            return False

        # Run extract_meta.py
        result = subprocess.run([
            'python3', extract_meta_path, extension_file
        ], capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Error running extract_meta.py: {result.stderr}")
            return False

        # Parse the JSON output
        metadata = json.loads(result.stdout)

        # Write to metainfo.json
        with open(metainfo_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=4, ensure_ascii=False)

        print(f"Generated {metainfo_file}")
        return True

    except Exception as e:
        print(f"Error generating metainfo.json for {extension_dir}: {e}")
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Add SHA256 checksums to EXTENSION files')
    parser.add_argument('directory', nargs='?', default='.',
                       help='Directory to search for EXTENSION files (default: current directory)')
    parser.add_argument('--force', action='store_true',
                       help='Force update even if SHA256 checksums already exist')

    args = parser.parse_args()

    print(f"Searching for EXTENSION files in {args.directory}")
    extension_files = find_extension_files(args.directory)

    print(f"Found {len(extension_files)} EXTENSION files")
    if args.force:
        print("Force mode enabled: will update existing SHA256 checksums")

    success_count = 0
    metainfo_count = 0

    for filepath in extension_files:
        print(f"\n{'='*60}")
        if process_extension_file(filepath, force_update=args.force):
            success_count += 1

            # Generate metainfo.json
            extension_dir = os.path.dirname(filepath)
            if generate_metainfo_json(extension_dir):
                metainfo_count += 1

    print(f"\n{'='*60}")
    print(f"Completed: {success_count}/{len(extension_files)} EXTENSION files processed successfully")
    print(f"Generated: {metainfo_count}/{len(extension_files)} metainfo.json files")


if __name__ == "__main__":
    main()
