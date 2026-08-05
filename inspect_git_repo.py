import os

def inspect_git_logs():
    log_file = os.path.join('.git', 'logs', 'HEAD')
    if not os.path.exists(log_file):
        print("[-] .git/logs/HEAD not found.")
        return

    print("=== FULL GIT COMMIT HISTORY LOG (.git/logs/HEAD) ===")
    commits = []
    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
        for idx, line in enumerate(f, 1):
            line_str = line.strip()
            if not line_str:
                continue
            parts = line_str.split('\t')
            header = parts[0]
            msg = parts[1] if len(parts) > 1 else ""
            commits.append((idx, header, msg))
    
    print(f"Total Commit Log Entries: {len(commits)}\n")
    for idx, header, msg in commits[-40:]: # Print last 40 commits
        print(f"[{idx}] {msg}")

def check_paper_directories():
    print("\n=== PAPER & PROGRESS DIRECTORY OVERVIEW ===")
    base_dir = "ProgressReport"
    if os.path.exists(base_dir):
        for root, dirs, files in os.walk(base_dir):
            rel = os.path.relpath(root, base_dir)
            if rel == ".":
                continue
            depth = rel.count(os.sep)
            if depth <= 2:
                file_count = len(files)
                tex_files = [f for f in files if f.endswith('.tex') or f.endswith('.pdf') or f.endswith('.md')]
                print(f"  {rel}/ -> {file_count} files (Docs/PDF/TeX: {len(tex_files)})")
                if tex_files:
                    print(f"     Sample files: {tex_files[:5]}")

if __name__ == '__main__':
    inspect_git_logs()
    check_paper_directories()
