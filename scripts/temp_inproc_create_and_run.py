import logging
import time
from fastapi.testclient import TestClient
from openhands.server.app import app

logger = logging.getLogger(__name__)
client = TestClient(app)
create_payload = {
    "repository": None,
    "git_provider": None,
    "selected_branch": None,
    "initial_user_msg": "initial message",
}
resp = client.post("/api/conversations", json=create_payload)
logger.info("create conversation status: %s %s", resp.status_code, resp.text)
conv = resp.json() if resp.status_code == 200 else None
conv_id = conv.get("conversation_id") if conv else None
logger.info("conv_id: %s", conv_id)
if not conv_id:
    logger.error("Could not create conversation; aborting")
else:
    r = client.post(f"/api/conversations/{conv_id}/metasop-debug", json={"message": "sop: hi"})
    logger.info("metasop-debug status: %s %s", r.status_code, r.text)
    r2 = client.post(f"/api/conversations/{conv_id}/events/raw", data="sop: hi", headers={"content-type": "text/plain"})
    logger.info("/events/raw status: %s %s", r2.status_code, r2.text)
    time.sleep(4)
