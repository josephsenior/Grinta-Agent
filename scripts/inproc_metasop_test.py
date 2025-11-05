import logging
import time
from fastapi.testclient import TestClient
from openhands.server.app import app


def run_test():
    logging.basicConfig(level=logging.DEBUG)
    client = TestClient(app)
    conv_id = "8cc289e6246847cc8b8f362902cdd55b"
    resp = client.post(f"/api/conversations/{conv_id}/metasop-debug", json={"message": "sop: inproc test run"})
    logging.getLogger(__name__).info("metasop-debug status: %s %s", resp.status_code, resp.text)
    resp2 = client.post(
        f"/api/conversations/{conv_id}/events/raw",
        data="sop: inproc raw message",
        headers={"content-type": "text/plain"},
    )
    logging.getLogger(__name__).info("/events/raw status: %s %s", resp2.status_code, resp2.text)
    time.sleep(3)


if __name__ == "__main__":
    run_test()
