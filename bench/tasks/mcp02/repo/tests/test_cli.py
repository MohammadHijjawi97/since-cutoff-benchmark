import pytest

from opsbot.calls import ToolCallFailed
from opsbot.cli import parse_pairs, render


def test_parse_pairs():
    assert parse_pairs(["service=api", "version=4.3.0"]) == {"service": "api", "version": "4.3.0"}
    with pytest.raises(ValueError):
        parse_pairs(["service"])


def test_render():
    assert render({"b": 1, "a": 2}) == '{\n  "a": 2,\n  "b": 1\n}'
    assert render("done") == "done"


def test_tool_call_failed_message():
    exc = ToolCallFailed("deploy", "no such version")
    assert (exc.tool, exc.message, str(exc)) == ("deploy", "no such version", "deploy failed: no such version")
