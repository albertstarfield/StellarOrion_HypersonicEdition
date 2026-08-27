import os

def search_git_logs_for_paperref():
    log_path = os.path.join('.git', 'logs', 'HEAD')
    if not os.path.exists(log_path):
        print("No .git/logs/HEAD found.")
        return

    print("=== SEARCHING GIT LOG FOR 'paperRef' / 'paper' / 'pdf' ===")
    matches = []
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for idx, line in enumerate(f, 1):
            line_lower = line.lower()
            if 'paperref' in line_lower or 'paper' in line_lower or 'pdf' in line_lower or 'ref' in line_lower:
                matches.append((idx, line.strip()))

    print(f"Found {len(matches)} matching commit log entries:\n")
    for idx, line in matches:
        parts = line.split('\t')
        commit_msg = parts[1] if len(parts) > 1 else parts[0]
        print(f"Commit #{idx}: {commit_msg}")

if __name__ == '__main__':
    search_git_logs_for_paperref()
