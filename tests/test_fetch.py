"""pcb/footprints/fetch.py retries what may pass on a second try, and only that; it reads the pin names from an
EasyEDA symbol."""
import importlib.util
import os
import sys
import urllib.error

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def fetch(monkeypatch):
    path = sys.path[:]                         # fetch.py puts pcb/ in front for its board import
    spec = importlib.util.spec_from_file_location("_fetch", os.path.join(ROOT, "pcb", "footprints", "fetch.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.path[:] = path
    monkeypatch.setattr(module.time, "sleep", lambda s: None)
    return module


def answers(monkeypatch, fetch, *errors):
    """urlopen raises the errors in turn, then answers; returns the list of tries"""
    tries = []

    class Answer:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self, *_):
            return b'{"result": 1}'

    def urlopen(req, timeout):
        tries.append(req.full_url)
        if len(tries) <= len(errors):
            raise errors[len(tries) - 1]
        return Answer()
    monkeypatch.setattr(fetch.urllib.request, "urlopen", urlopen)
    return tries


def http(code):
    return urllib.error.HTTPError("u", code, "x", {}, None)


@pytest.mark.parametrize("code", [403, 404])
def test_client_errors_are_not_retried(monkeypatch, fetch, code):
    tries = answers(monkeypatch, fetch, http(code))
    with pytest.raises(urllib.error.HTTPError):
        fetch.download("https://example.invalid/")
    assert len(tries) == 1


@pytest.mark.parametrize("error", [http(429), http(503), urllib.error.URLError("down"), TimeoutError(),
                                   ConnectionResetError()])
def test_transient_errors_are_retried(monkeypatch, fetch, error):
    tries = answers(monkeypatch, fetch, error, error)
    assert fetch.download("https://example.invalid/") == {"result": 1} and len(tries) == 3


def test_pin_names_come_with_their_pad_numbers(fetch):
    # the two pins of JLC's symbol of the 1N4148W (C81598) as EasyEDA sends them, between two other shapes
    shapes = [
        "PL~-5 8 -5 -8~#880000~1~0~none~gge3~0",
        "P~show~0~2~20~0~0~gge8~0^^20~0^^M 20 0 h -15~#880000^^0~2~3~0~A~end~~~#0000FF^^0~11~-1~0~2~start~~~#0000FF"
        "^^0~8~0^^0~M 5 -3 L 2 0 L 5 3",
        "P~show~0~1~-20~0~180~gge17~0^^-20~0^^M -20 0 h 15~#880000^^0~-2~3~0~K~start~~~#0000FF^^0~-11~-1~0~1~end~~~"
        "#0000FF^^0~-8~0^^0~M -5 3 L -2 0 L -5 -3",
        "PG~5 -8 5 8~#880000~1~0~none~gge20~0",
    ]
    assert fetch.pins_of({"dataStr": {"shape": shapes}}) == [("1", "K"), ("2", "A")]
