import json
import logging
import subprocess
import sys
import time
import urllib.request

logger = logging.getLogger(__name__)
CONTAINER = "Forge-app"
CONVERSATION_ID = "8cc289e6246847cc8b8f362902cdd55b"
URL = f"http://localhost:3000/api/conversations/{CONVERSATION_ID}/metasop-debug"


def tail_logs():
    return subprocess.Popen(
        ["docker", "logs", "-f", CONTAINER, "--tail", "200"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def call_endpoint(message=None):
    data = {}
    if message:
        data["message"] = message
    req = urllib.request.Request(
        URL, data=json.dumps(data).encode("utf-8"), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310 - Safe: accessing localhost API in debug script
        return resp.read().decode("utf-8")


def main():
    logger.info("Starting docker logs tail...")
    logs = tail_logs()
    time.sleep(1)
    logger.info("Calling metasop-debug endpoint...")
    try:
        resp = call_endpoint("sop: automated debug run")
        logger.info("Endpoint response: %s", resp)
    except Exception as e:
        logger.exception("Endpoint call failed: %s", e)
        logs.kill()
        sys.exit(1)
    start = time.time()
    try:
        while time.time() - start < 10:
            if line := logs.stdout.readline():
                logger.info(line.rstrip())
            else:
                break
    finally:
        logs.kill()


if __name__ == "__main__":
    main()
