"""Invoice processing with Claude (0.x-era structured outputs: `output_format` on beta create).

Invoices are uploaded once by the intake job with the Files API and are referenced here by their
file id. File references only work on the beta Messages API with FILES_BETA enabled, so every call
in this module goes through `client.beta.messages`.
"""

import json

from anthropic import Anthropic

from app.schemas import INVOICE_SCHEMA

MODEL = "claude-opus-5-5"
FILES_BETA = "files-api-2025-04-14"
STRUCTURED_OUTPUTS_BETA = "structured-outputs-2025-11-13"


def invoice_block(file_id: str) -> dict:
    """A document content block pointing at an uploaded invoice PDF."""
    return {"type": "document", "source": {"type": "file", "file_id": file_id}}


def summarize_invoice(client: Anthropic, file_id: str) -> str:
    """One-paragraph summary for the accounts-payable review queue."""
    message = client.beta.messages.create(
        model=MODEL,
        max_tokens=512,
        betas=[FILES_BETA],
        messages=[
            {
                "role": "user",
                "content": [
                    invoice_block(file_id),
                    {"type": "text", "text": "Summarize this invoice in one paragraph for an accounts-payable clerk."},
                ],
            }
        ],
    )
    return "".join(block.text for block in message.content if block.type == "text").strip()


def extract_invoice(client: Anthropic, file_id: str) -> dict:
    """The invoice's fields as one ledger import row (see INVOICE_SCHEMA)."""
    message = client.beta.messages.create(
        model=MODEL,
        max_tokens=1024,
        betas=[FILES_BETA, STRUCTURED_OUTPUTS_BETA],
        messages=[
            {
                "role": "user",
                "content": [
                    invoice_block(file_id),
                    {"type": "text", "text": "Extract the ledger import fields from this invoice."},
                ],
            }
        ],
        output_format={"type": "json_schema", "schema": INVOICE_SCHEMA},
    )
    text = "".join(block.text for block in message.content if block.type == "text")
    return json.loads(text)
