import urllib.request

url = "https://api.github.com/repos/josephsenior/Grinta-Coding-Agent/actions/jobs/89188021980/logs"
req = urllib.request.Request(url, headers={"User-Agent": "Python"})

try:
    with urllib.request.urlopen(req) as resp:
        content = resp.read().decode('utf-8', errors='replace')
        lines = content.splitlines()
        print(f"Total log lines: {len(lines)}")
        # Print failure lines
        fail_lines = [line for line in lines if 'FAIL' in line or 'FAILED' in line or 'ERROR' in line or 'AssertionError' in line]
        for l in fail_lines[-30:]:
            print(l)
except Exception as e:
    print(f"Error fetching log: {e}")
