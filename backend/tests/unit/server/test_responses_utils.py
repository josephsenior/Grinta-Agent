import json
import pytest

from forge.server.utils.responses import success, error, SUCCESS_STATUS, ERROR_STATUS


def _body_json(resp):
    # FastAPI JSONResponse body is bytes
    return json.loads(resp.body.decode("utf-8"))


def test_success_minimal_defaults():
    resp = success()
    assert resp.status_code == 200
    body = _body_json(resp)
    assert body["status"] == SUCCESS_STATUS
    assert "data" not in body
    assert "message" not in body
    assert "meta" not in body


def test_success_with_payload_and_meta_and_message():
    data = {"a": 1}
    resp = success(data, message="done", status_code=201, request_id="abc", extra=True)
    assert resp.status_code == 201
    body = _body_json(resp)
    assert body == {
        "status": SUCCESS_STATUS,
        "message": "done",
        "data": {"a": 1},
        "meta": {"request_id": "abc", "extra": True},
    }


def test_error_minimal():
    resp = error(message="bad request")
    assert resp.status_code == 400
    body = _body_json(resp)
    assert body == {"status": ERROR_STATUS, "message": "bad request"}


def test_error_full_envelope():
    details = {"field": "name", "issue": "required"}
    actions = [{"label": "Retry", "action": "retry"}]
    resp = error(
        message="validation failed",
        status_code=422,
        error_code="VALIDATION_ERROR",
        details=details,
        actions=actions,
        request_id="xyz",
    )
    assert resp.status_code == 422
    body = _body_json(resp)
    assert body == {
        "status": ERROR_STATUS,
        "message": "validation failed",
        "error_code": "VALIDATION_ERROR",
        "details": {"field": "name", "issue": "required"},
        "actions": [{"label": "Retry", "action": "retry"}],
        "meta": {"request_id": "xyz"},
    }
