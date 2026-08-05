import os

def find_all_paper_files():
    search_dirs = [".", "ProgressReport", "docs"]
    extensions = ('.tex', '.pdf', '.bib', '.md', '.docx', '.doc')
    
    found_files = []
    for s_dir in search_dirs:
        if not os.path.exists(s_dir):
            continue
        for root, dirs, files in os.walk(s_dir):
            # Skip hidden dirs except .git if needed
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                if f.lower().endswith(extensions):
                    full_path = os.path.join(root, f)
                    size_kb = round(os.path.getsize(full_path) / 1024.0, 2)
                    found_files.append((full_path, size_kb))

    print(f"=== FOUND {len(found_files)} DOCUMENT / PAPER FILES ===")
    for path, size in sorted(found_files, key=lambda x: x[0]):
        print(f"[{size} KB] {path}")

if __name__ == '__main__':
    find_all_paper_files()
