"""oai02 hidden tests: mock_openai() must intercept every sync OpenAI request inside the block, and only there.

Written to run at both openai 3.19.2 (pinned) and 2.44.0 (cutoff era). No request may reach the network: the
grader points HTTP(S)_PROXY at a dead local port and pytest-socket only allows 127.0.0.1.
"""

import openai
import pytest

from app import digest
from tests.fakes import mock_openai


def ask(client, text):
    completion = client.chat.completions.create(
        model="gpt-5.5-mini", messages=[{"role": "user", "content": text}]
    )
    return completion.choices[0].message.content


def test_app_cached_client_created_before_the_block_is_intercepted():
    digest.get_client.cache_clear()
    digest.get_client()  # created outside any fake, as in production code paths
    with mock_openai("Refund issued twice.", "Duplicate refund reversed and customer informed.") as seen:
        assert digest.headline("thread 17") == "Refund issued twice"
        assert digest.summarize("thread 17") == "Duplicate refund reversed and customer informed."
    assert [body["model"] for body in seen] == [digest.MODEL, digest.MODEL]
    assert [body["max_completion_tokens"] for body in seen] == [24, 200]
    assert seen[1]["messages"][-1] == {"role": "user", "content": "thread 17"}


def test_clients_created_before_and_inside_the_block_share_the_replies_in_order():
    early = openai.OpenAI(api_key="sk-test-early", max_retries=0)
    with mock_openai("one", "two", "three") as seen:
        late = openai.OpenAI(api_key="sk-test-late", max_retries=0)
        assert ask(early, "a") == "one"
        assert ask(late, "b") == "two"
        assert ask(early, "c") == "three"
    assert [body["messages"][0]["content"] for body in seen] == ["a", "b", "c"]


def test_consecutive_blocks_are_independent():
    client = openai.OpenAI(api_key="sk-test", max_retries=0)
    with mock_openai("first") as first:
        assert ask(client, "x") == "first"
    with mock_openai("second") as second:
        assert ask(client, "y") == "second"
    assert [b["messages"][0]["content"] for b in first] == ["x"]
    assert [b["messages"][0]["content"] for b in second] == ["y"]


def test_nothing_is_intercepted_after_the_block():
    client = openai.OpenAI(api_key="sk-test", max_retries=0, timeout=10.0)
    with mock_openai("inside") as seen:
        assert ask(client, "in") == "inside"
    # outside the block the request must not be answered by the fake; the real API is unreachable here
    with pytest.raises(Exception):
        ask(client, "out")
    assert len(seen) == 1
