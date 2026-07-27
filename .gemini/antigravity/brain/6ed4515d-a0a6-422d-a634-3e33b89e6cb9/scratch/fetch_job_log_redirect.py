import urllib.request

url = "https://api.github.com/repos/josephsenior/Grinta-Coding-Agent/actions/jobs/89188021980/logs"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

try:
    with urllib.request.urlopen(req) as resp:
        content = resp.read().decode('utf-8', errors='replace')
        lines = content.splitlines()
        print(f"Total log lines: {len(lines)}")
        # Print failure lines
        for i, line in enumerate(lines):
            if 'FAILED' in line or 'FAIL ' in line or '=== FAILURES ===' in line:
                print("\n".join(lines[max(0, i-5):min(len(lines), i+30)]))
                break
except Exception as e:
    print(f"Error fetching log: {e}")
