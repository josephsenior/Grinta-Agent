from types import SimpleNamespace

from forge.utils.tenacity_stop import stop_if_should_exit


def test_stop_if_should_exit(monkeypatch):
    stopper = stop_if_should_exit()

    monkeypatch.setattr("forge.utils.tenacity_stop.should_exit", lambda: False)
    assert stopper(SimpleNamespace()) is False

    monkeypatch.setattr("forge.utils.tenacity_stop.should_exit", lambda: True)
    assert stopper(SimpleNamespace()) is True

