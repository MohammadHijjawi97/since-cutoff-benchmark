"""oai04 hidden tests (no-change control): Responses API request shape, reply text and truncation flag.

Runs at openai 3.19.2 (pinned) and 2.44.0 (cutoff era); nothing the task needs changed between them.
"""

import json

import openai

try:
    import httpx2 as hx
except ImportError:  # pragma: no cover - openai<3
    import httpx as hx

from app.drafts import DRAFT_MODEL, MAX_DRAFT_TOKENS, STYLE_GUIDE, Draft, Ticket, draft_reply

TICKET = Ticket(id="T-4711", subject="Dashboard down", body="Our status dashboard shows 502 errors since 09:10 UTC.")


def response_json(*texts, status="completed", reason=None):
    return {
        "id": "resp_0a1b", "object": "response", "created_at": 1767225600, "model": DRAFT_MODEL,
        "status": status, "error": None,
        "incomplete_details": {"reason": reason} if reason else None,
        "instructions": STYLE_GUIDE, "metadata": {"ticket_id": TICKET.id}, "parallel_tool_calls": True,
        "temperature": 1.0, "top_p": 1.0, "tool_choice": "auto", "tools": [], "store": False,
        "output": [
            {"type": "reasoning", "id": "rs_0a1b", "summary": []},
            {"type": "message", "id": "msg_0a1b", "role": "assistant",
             "status": "completed" if status == "completed" else "incomplete",
             "content": [{"type": "output_text", "text": t, "annotations": []} for t in texts]},
        ],
        "usage": {"input_tokens": 91, "output_tokens": 120, "total_tokens": 211,
                  "input_tokens_details": {"cached_tokens": 0}, "output_tokens_details": {"reasoning_tokens": 64}},
    }


def client_for(payload, seen):
    def handler(request):
        seen.append((request.method, request.url.path, json.loads(request.content)))
        return hx.Response(200, json=payload)
    http_client = openai.DefaultHttpxClient(transport=hx.MockTransport(handler))
    return openai.OpenAI(api_key="sk-test", max_retries=0, http_client=http_client)


def test_request_shape_and_reply_text():
    seen = []
    payload = response_json("  Hi Dana,\n\nWe found the cause of the 502 errors ", "and rolled back the release.\n")
    draft = draft_reply(client_for(payload, seen), TICKET)
    assert draft == Draft(ticket_id="T-4711",
                          text="Hi Dana,\n\nWe found the cause of the 502 errors and rolled back the release.",
                          truncated=False)
    assert len(seen) == 1
    method, path, body = seen[0]
    assert (method, path) == ("POST", "/v1/responses")
    assert body["model"] == DRAFT_MODEL
    assert body["instructions"] == STYLE_GUIDE
    assert body["max_output_tokens"] == MAX_DRAFT_TOKENS
    assert body["store"] is False
    assert body["metadata"] == {"ticket_id": "T-4711"}
    sent = json.dumps(body["input"])
    assert "Dashboard down" in sent and "502 errors since 09:10 UTC" in sent


def test_cut_off_at_the_token_cap_is_flagged_as_truncated():
    payload = response_json("Hi Dana,\n\nWe found the cause and ", status="incomplete", reason="max_output_tokens")
    draft = draft_reply(client_for(payload, []), TICKET)
    assert draft.truncated is True
    assert draft.text == "Hi Dana,\n\nWe found the cause and"


def test_incomplete_for_another_reason_is_not_truncation():
    payload = response_json("Hi Dana,", status="incomplete", reason="content_filter")
    draft = draft_reply(client_for(payload, []), TICKET)
    assert draft.truncated is False
    assert draft.text == "Hi Dana,"
