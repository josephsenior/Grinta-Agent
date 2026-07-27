import os

log_path = r"C:\Users\ymejdi\.gemini\antigravity\brain\6ed4515d-a0a6-422d-a634-3e33b89e6cb9\.system_generated\tasks\task-710.log"

if os.path.exists(log_path):
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        print(f"Total lines: {len(lines)}")
        for line in lines:
            if 'FAIL' in line or 'ERROR' in line or 'AssertionError' in line or 'Exception' in line:
                print(line.strip())
else:
    print("Log file not found")
