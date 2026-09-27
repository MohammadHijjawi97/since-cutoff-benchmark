"""Probe: what does messages.parse(stream=True) do at each anthropic version?"""
import json
import sys
import warnings

import anthropic
import pydantic

try:
    import httpx2 as hx
except ImportError:
    import httpx as hx

print("anthropic", anthropic.__version__, "http lib", hx.__name__)

MODEL = "claude-opus-5-5"
RESULT = {"title": "Fix login", "priority": 2}


def sse_events():
    text = json.dumps(RESULT)
    half = len(text) // 2
    msg = {"id": "msg_1", "type": "message", "role": "assistant", "model": MODEL, "content": [],
           "stop_reason": None, "stop_sequence": None, "usage": {"input_tokens": 5, "output_tokens": 1}}
    evs = [
        ("message_start", {"type": "message_start", "message": msg}),
        ("content_block_start", {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}}),
        ("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": text[:half]}}),
        ("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": text[half:]}}),
        ("content_block_stop", {"type": "content_block_stop", "index": 0}),
        ("message_delta", {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None}, "usage": {"output_tokens": 9}}),
        ("message_stop", {"type": "message_stop"}),
    ]
    return "".join(f"event: {e}\ndata: {json.dumps(d)}\n\n" for e, d in evs).encode()


def handler(request):
    body = json.loads(request.content)
    print("  request body keys:", sorted(body), "stream:", body.get("stream"), "output_config:", body.get("output_config"))
    if body.get("stream"):
        return hx.Response(200, headers={"content-type": "text/event-stream"}, content=sse_events())
    msg = {"id": "msg_1", "type": "message", "role": "assistant", "model": MODEL,
           "content": [{"type": "text", "text": json.dumps(RESULT)}], "stop_reason": "end_turn",
           "stop_sequence": None, "usage": {"input_tokens": 5, "output_tokens": 9}}
    return hx.Response(200, json=msg)


class Ticket(pydantic.BaseModel):
    title: str
    priority: int


client = anthropic.Anthropic(api_key="k", max_retries=0,
                             http_client=anthropic.DefaultHttpxClient(transport=hx.MockTransport(handler)))

print("A) messages.parse(stream=True, output_format=Ticket)")
try:
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        r = client.messages.parse(model=MODEL, max_tokens=100, messages=[{"role": "user", "content": "x"}],
                                  output_format=Ticket, stream=True)
    print("  returned", type(r), repr(r)[:300])
    print("  parsed_output:", getattr(r, "parsed_output", "<none>"))
    print("  warnings:", [str(x.message)[:100] for x in w])
except Exception as exc:
    print("  RAISED", type(exc).__name__, str(exc)[:300])

print("B) messages.stream(output_format=Ticket)")
try:
    with client.messages.stream(model=MODEL, max_tokens=100, messages=[{"role": "user", "content": "x"}],
                                output_format=Ticket) as s:
        chunks = list(s.text_stream)
        final = s.get_final_message()
    print("  chunks", chunks, "parsed_output:", getattr(final, "parsed_output", "<none>"))
except Exception as exc:
    print("  RAISED", type(exc).__name__, str(exc)[:300])

print("C) messages.stream(output_format=<dict schema>)")
try:
    schema = {"type": "json_schema", "schema": Ticket.model_json_schema() | {"additionalProperties": False}}
    with client.messages.stream(model=MODEL, max_tokens=100, messages=[{"role": "user", "content": "x"}],
                                output_format=schema) as s:
        chunks = list(s.text_stream)
    print("  chunks", chunks)
except Exception as exc:
    print("  RAISED", type(exc).__name__, str(exc)[:300])

print("D) messages.create(stream=True) + output_config")
try:
    schema = {"type": "json_schema", "schema": Ticket.model_json_schema() | {"additionalProperties": False}}
    evs = client.messages.create(model=MODEL, max_tokens=100, messages=[{"role": "user", "content": "x"}],
                                 output_config={"format": schema}, stream=True)
    print("  events", [e.type for e in evs])
except Exception as exc:
    print("  RAISED", type(exc).__name__, str(exc)[:300])

print("E) parse(stream=True) when the mock always returns JSON (ignores stream flag)")


def json_handler(request):
    msg = {"id": "msg_1", "type": "message", "role": "assistant", "model": MODEL,
           "content": [{"type": "text", "text": json.dumps(RESULT)}], "stop_reason": "end_turn",
           "stop_sequence": None, "usage": {"input_tokens": 5, "output_tokens": 9}}
    return hx.Response(200, json=msg)


c2 = anthropic.Anthropic(api_key="k", max_retries=0,
                         http_client=anthropic.DefaultHttpxClient(transport=hx.MockTransport(json_handler)))
try:
    r = c2.messages.parse(model=MODEL, max_tokens=100, messages=[{"role": "user", "content": "x"}],
                          output_format=Ticket, stream=True)
    print("  returned", type(r).__name__, "parsed_output:", getattr(r, "parsed_output", "<none>"))
except Exception as exc:
    print("  RAISED", type(exc).__name__, str(exc)[:300])
