import os
import subprocess
import zlib
import re

def search_git_objects():
    objects_dir = os.path.join('.git', 'objects')
    if not os.path.exists(objects_dir):
        print("[-] .git/objects directory not found.")
        return

    print("=== SEARCHING LOOSE GIT OBJECTS FOR 'paperRef' OR '.pdf' ===")
    found_pdfs = set()
    found_paperref_files = set()

    for root, dirs, files in os.walk(objects_dir):
        for f in files:
            if len(f) == 38: # Loose git object hash string remainder
                obj_path = os.path.join(root, f)
                try:
                    with open(obj_path, 'rb') as obj_file:
                        data = zlib.decompress(obj_file.read())
                        # Decode printable strings
                        text = data.decode('utf-8', errors='ignore')
                        if 'paperref' in text.lower() or 'pdf' in text.lower():
                            # Find filenames ending with .pdf or paths with paperRef
                            pdfs = re.findall(r'[\w\-\./]+\.pdf', text, re.IGNORECASE)
                            paperrefs = re.findall(r'[\w\-\./]*paperref[\w\-\./]*', text, re.IGNORECASE)
                            for p in pdfs:
                                found_pdfs.add(p)
                            for pr in paperrefs:
                                found_paperref_files.add(pr)
                except Exception:
                    continue

    print(f"\n[+] Found {len(found_pdfs)} PDF references across git history:")
    for pdf in sorted(found_pdfs):
        print(f"  - {pdf}")

    print(f"\n[+] Found {len(found_paperref_files)} paperRef path references across git history:")
    for pr in sorted(found_paperref_files):
        print(f"  - {pr}")

if __name__ == '__main__':
    search_git_objects()
