"""ant03: structured outputs on the beta Messages API (anthropic 1.8.0; stale form passes at 0.115.0).

Offline: the Anthropic client talks to a MockTransport. Checks what goes over the wire (the JSON-schema
output format carrying INVOICE_SCHEMA, the beta endpoint with the Files API beta, the file reference) and
what the function returns.
"""

import json

import anthropic

try:
    import httpx2 as hx
except ImportError:  # pragma: no cover - anthropic<1
    import httpx as hx

from app.invoices import FILES_BETA, MODEL, extract_invoice
from app.schemas import INVOICE_SCHEMA

FILE_ID = "file_011CPMxVD3fHLUhvTqtsQA5w"


def reply_body(record: dict) -> dict:
    return {
        "id": "msg_03", "type": "message", "role": "assistant", "model": MODEL,
        "content": [{"type": "text", "text": json.dumps(record)}],
        "stop_reason": "end_turn", "stop_sequence": None,
        "usage": {"input_tokens": 1450, "output_tokens": 48},
    }


def make_client(record: dict, seen: list) -> anthropic.Anthropic:
    def handler(request):
        seen.append(request)
        return hx.Response(200, headers={"request-id": "req_ant03"}, json=reply_body(record))

    return anthropic.Anthropic(
        api_key="test-key", max_retries=0,
        http_client=anthropic.DefaultHttpxClient(transport=hx.MockTransport(handler)),
    )


def shape(schema: dict) -> dict:
    """What the schema constrains (property types, required keys, no extra keys), ignoring titles and descriptions."""
    return {
        "type": schema.get("type"),
        "properties": {name: prop.get("type") for name, prop in schema.get("properties", {}).items()},
        "required": sorted(schema.get("required", [])),
        "additionalProperties": schema.get("additionalProperties"),
    }


def test_requests_structured_output_with_the_invoice_schema():
    record = {"invoice_number": "INV-2041", "vendor": "Acme Tools GmbH", "issue_date": "2026-09-01",
              "currency": "EUR", "total": 1234.5}
    seen: list = []
    result = extract_invoice(make_client(record, seen), FILE_ID)

    assert len(seen) == 1, "exactly one API request"
    request = seen[0]
    body = json.loads(request.content)
    assert request.url.path == "/v1/messages"
    assert request.url.params.get("beta") == "true", "file references need the beta Messages API"
    assert FILES_BETA in request.headers.get("anthropic-beta", "")
    assert body["model"] == MODEL
    assert body["max_tokens"] == 1024
    assert FILE_ID in json.dumps(body["messages"])

    fmt = (body.get("output_config") or {}).get("format")
    assert fmt, f"no structured output format in the request: {sorted(body)}"
    assert fmt["type"] == "json_schema"
    assert shape(fmt["schema"]) == shape(INVOICE_SCHEMA)

    assert result == record
    json.dumps(result)  # the ledger import serialises the row


def test_returns_what_the_model_produced():
    record = {"invoice_number": "2026/0917", "vendor": "Nordwind Logistik", "issue_date": "2026-09-17",
              "currency": "SEK", "total": 88900}
    assert extract_invoice(make_client(record, []), "file_02") == record
