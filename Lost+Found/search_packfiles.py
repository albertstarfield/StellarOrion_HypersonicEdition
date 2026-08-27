import os
import glob
import re

def search_packfiles():
    pack_dir = os.path.join('.git', 'objects', 'pack')
    if not os.path.exists(pack_dir):
        print("[-] No pack directory found.")
        return

    pack_files = glob.glob(os.path.join(pack_dir, "*.pack"))
    idx_files = glob.glob(os.path.join(pack_dir, "*.idx"))

    print(f"=== FOUND {len(pack_files)} PACKFILES & {len(idx_files)} INDEX FILES ===")
    
    matches = set()
    for p_file in pack_files:
        print(f"Scanning packfile: {p_file} ({round(os.path.getsize(p_file)/(1024*1024), 2)} MB)...")
        with open(p_file, 'rb') as f:
            content = f.read()
            # Search for printable filenames/strings
            pdf_matches = re.findall(rb'[\w\-\./]+\.pdf', content, re.IGNORECASE)
            paperref_matches = re.findall(rb'[\w\-\./]*paperref[\w\-\./]*', content, re.IGNORECASE)
            
            for m in pdf_matches:
                matches.add(m.decode('utf-8', errors='ignore'))
            for m in paperref_matches:
                matches.add(m.decode('utf-8', errors='ignore'))

    print(f"\n[+] Found {len(matches)} matching string references inside packfiles:")
    for m in sorted(matches):
        print(f"  - {m}")

if __name__ == '__main__':
    search_packfiles()
