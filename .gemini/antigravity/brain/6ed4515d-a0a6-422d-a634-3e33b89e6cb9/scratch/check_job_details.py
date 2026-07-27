import urllib.request
import json

url = "https://api.github.com/repos/josephsenior/Grinta-Coding-Agent/actions/runs/30001664142/jobs"
req = urllib.request.Request(url, headers={"User-Agent": "Python", "Accept": "application/vnd.github+json"})

with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    for job in data.get('jobs', []):
        if job.get('conclusion') == 'failure':
            print(f"Job: {job.get('name')} ID: {job.get('id')}")
            # Print steps details
            for step in job.get('steps', []):
                print(f"  Step: {step.get('name')} -> {step.get('conclusion')}")
