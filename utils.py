import os

EXTENSION_TO_SKIP = [
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".ico", ".tif", ".tiff",
    "yarn.lock", "package-lock.json", "node_modules", ".git", 'logs.md'
]
EXCLUDED_DIRS = ['node_modules', '.git']

def read_file(filename):
    with open(filename, 'r') as file:
        return file.read()

def walk_directory(directory):
    code_contents = {}
    for dirpath, dirnames, filenames in os.walk(directory):
        for exclude_dir in EXCLUDED_DIRS:
          if exclude_dir in dirnames:
              dirnames.remove(exclude_dir)
      
        for filename in filenames:
            if not any(filename.endswith(ext) for ext in EXTENSION_TO_SKIP):
                try:
                    relative_filepath = os.path.relpath(os.path.join(dirpath, filename), directory)
                    code_contents[relative_filepath] = read_file(os.path.join(dirpath, filename))
                except Exception as e:
                    code_contents[relative_filepath] = f"Error reading file {filename}: {str(e)}"  # type: ignore
    return code_contents
