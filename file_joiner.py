#!/usr/bin/env python3
import os
import glob
import argparse
from pathlib import Path
from datetime import datetime
import platform
import chardet
import re

SEARCH_DIRECTORY = "/home/danand/qcs_infra_tf" if platform.system() != "Windows" else "C:\\dev\\python-projects\\OI-AI-Strategy"
DEFAULT_EXTENSIONS = ["*.py","*.html"]
OUTPUT_FILENAME_PREFIX = "complete_code"
ENCODING = "utf-8"
DELIMITER = "=" * 80
RECURSIVE_SEARCH = False

def normalize_path(path):
    if platform.system() == "Windows":
        path = path.replace('\\', '\\\\')
    return path

def detect_encoding(file_path):
    try:
        with open(file_path, 'rb') as file:
            raw_data = file.read()
            result = chardet.detect(raw_data)
            encoding = result['encoding']
            confidence = result['confidence']
            if encoding is None or confidence < 0.7:
                return 'utf-8'
            return encoding
    except Exception as e:
        print(f"Warning: Could not detect encoding for {file_path}, using utf-8: {e}")
        return 'utf-8'

def read_file_with_fallback(file_path):
    encodings_to_try = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1', 'utf-16']
    for encoding in encodings_to_try:
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                return file.read(), encoding
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"Error reading {file_path} with {encoding}: {e}")
            continue
    try:
        detected_encoding = detect_encoding(file_path)
        with open(file_path, 'r', encoding=detected_encoding) as file:
            return file.read(), detected_encoding
    except Exception as e:
        print(f"Final fallback failed for {file_path}: {e}")
        return None, None

def minify_content(content, file_extension):
    if not content:
        return content
    
    minified = content
    
    if file_extension in ['.py', '.tf', '.js', '.java', '.c', '.cpp', '.cs']:
        minified = re.sub(r'#.*$', '', minified, flags=re.MULTILINE)
    
    if file_extension in ['.js', '.java', '.c', '.cpp', '.cs', '.css']:
        minified = re.sub(r'//.*$', '', minified, flags=re.MULTILINE)
        minified = re.sub(r'/\*.*?\*/', '', minified, flags=re.DOTALL)
    
    if file_extension in ['.html', '.xml']:
        minified = re.sub(r'<!--.*?-->', '', minified, flags=re.DOTALL)
    
    minified = re.sub(r'^\s*$\n', '', minified, flags=re.MULTILINE)
    
    minified = re.sub(r'[ \t]+', ' ', minified)
    
    minified = re.sub(r'\n\s*\n', '\n', minified)
    
    minified = re.sub(r'[ \t]+\n', '\n', minified)
    
    minified = re.sub(r'{\s+', '{', minified)
    minified = re.sub(r'\s+}', '}', minified)
    minified = re.sub(r'\(\s+', '(', minified)
    minified = re.sub(r'\s+\)', ')', minified)
    minified = re.sub(r'\[\s+', '[', minified)
    minified = re.sub(r'\s+\]', ']', minified)
    
    minified = re.sub(r';\s+;', ';', minified)
    minified = re.sub(r',\s+,', ',', minified)
    
    minified = minified.strip()
    
    return minified

def get_output_filename(prefix, extensions):
    date_str = datetime.now().strftime("%Y%m%d")
    ext_str = "_".join([ext.replace('*.', '') for ext in extensions])
    return f"{prefix}_{date_str}_{ext_str}.txt"

def combine_tf_files(search_dir, output_file, file_extensions, include_hidden=False):
    try:
        search_dir = normalize_path(search_dir)
        search_path = Path(search_dir)
        
        if not search_path.exists():
            print(f"Error: Directory '{search_dir}' does not exist")
            return False
        
        output_path = search_path / output_file
        
        all_files = []
        for extension in file_extensions:
            if RECURSIVE_SEARCH:
                pattern = "**/" + extension
            else:
                pattern = extension
            
            files_found = list(search_path.glob(pattern))
            
            if not include_hidden:
                files_found = [f for f in files_found if not any(part.startswith('.') for part in f.parts)]
            
            all_files.extend(files_found)
        
        all_files = list(set(all_files))
        
        if not all_files:
            extensions_str = ", ".join(file_extensions)
            print(f"No files matching {extensions_str} found in {search_dir}")
            print(f"Recursive search was: {'enabled' if RECURSIVE_SEARCH else 'disabled'}")
            return False
        
        print(f"Found {len(all_files)} files matching extensions: {', '.join(file_extensions)}")
        print(f"Recursive search: {RECURSIVE_SEARCH}")
        
        with open(output_path, 'w', encoding=ENCODING) as outfile:
            outfile.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            outfile.write(f"Combined All file content of {', '.join(file_extensions)} files\n")
            outfile.write(f"From Directory: {search_dir}\n")
            outfile.write(f"Recursive Search: {RECURSIVE_SEARCH}\n")
            outfile.write(f"Total Files: {len(all_files)}\n")
            outfile.write(DELIMITER + "\n\n")
            
            for file_path in sorted(all_files):
                try:
                    relative_path = file_path.relative_to(search_path)
                    print(f"Processing: {relative_path}")
                    
                    outfile.write(f"\n{DELIMITER}\n")
                    outfile.write(f"FILE: {relative_path}\n")
                    outfile.write(f"EXTENSION: {file_path.suffix}\n")
                    outfile.write(f"FULL PATH: {file_path}\n")
                    
                    content, used_encoding = read_file_with_fallback(file_path)
                    
                    if content is None:
                        outfile.write(f"ENCODING: FAILED TO READ FILE\n")
                        outfile.write(f"{DELIMITER}\n\n")
                        print(f"Error: Could not read {file_path} (all encoding attempts failed)")
                        continue
                    
                    original_size = len(content)
                    minified_content = minify_content(content, file_path.suffix.lower())
                    minified_size = len(minified_content)
                    
                    outfile.write(f"ENCODING: {used_encoding}\n")
                    outfile.write(f"ORIGINAL SIZE: {original_size} bytes\n")
                    outfile.write(f"MINIFIED SIZE: {minified_size} bytes\n")
                    outfile.write(f"SIZE REDUCTION: {((original_size - minified_size) / original_size * 100):.1f}%\n")
                    outfile.write(f"{DELIMITER}\n\n")
                    
                    outfile.write(minified_content)
                    
                    outfile.write("\n\n")
                    
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    outfile.write(f"\n{DELIMITER}\n")
                    outfile.write(f"FILE: {relative_path}\n")
                    outfile.write(f"ERROR: {e}\n")
                    outfile.write(f"{DELIMITER}\n\n")
                    continue
        
        print(f"Successfully combined {len(all_files)} files into {output_path}")
        return True
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def parse_extensions(extensions_str):
    if not extensions_str:
        return DEFAULT_EXTENSIONS
    
    extensions = [ext.strip() for ext in extensions_str.split(',')]
    
    parsed_extensions = []
    for ext in extensions:
        if not ext.startswith('*'):
            if not ext.startswith('.'):
                ext = '.' + ext
            ext = '*' + ext
        parsed_extensions.append(ext)
    
    return parsed_extensions

def main():
    search_directory = SEARCH_DIRECTORY
    file_extensions = DEFAULT_EXTENSIONS
    include_hidden = False
    recursive = RECURSIVE_SEARCH
    
    output_filename = get_output_filename(OUTPUT_FILENAME_PREFIX, file_extensions)
    
    print(f"Platform: {platform.system()}")
    print(f"Searching directory: {search_directory}")
    print(f"File extensions: {', '.join(file_extensions)}")
    print(f"Output file: {output_filename}")
    print(f"Output location: {search_directory}")
    print(f"Include hidden files: {include_hidden}")
    print(f"Recursive search: {recursive}")
    print("-" * 50)
    
    success = combine_tf_files(
        search_directory, 
        output_filename, 
        file_extensions, 
        include_hidden
    )
    
    if success:
        output_path = Path(normalize_path(search_directory)) / output_filename
        print(f"\n✅ Completed! Check {output_path}")
        
        if output_path.exists():
            file_size = output_path.stat().st_size
            print(f"Output file size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
    else:
        print(f"\n❌ Failed to combine files")
        exit(1)

if __name__ == "__main__":
    main()