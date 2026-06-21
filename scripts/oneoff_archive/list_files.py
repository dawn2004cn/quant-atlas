import os
import glob

def list_files():
    files = glob.glob("**/*.md", recursive=True)
    with open("file_list.txt", "w", encoding="utf-8") as f:
        for file in files:
            f.write(file + "\n")

if __name__ == "__main__":
    list_files()
