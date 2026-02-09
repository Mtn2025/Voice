
import os
import shutil

def clean_pycache():
    root_dir = os.getcwd()
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if "__pycache__" in dirnames:
            path = os.path.join(dirpath, "__pycache__")
            print(f"Removing {path}...")
            shutil.rmtree(path)

if __name__ == "__main__":
    clean_pycache()
