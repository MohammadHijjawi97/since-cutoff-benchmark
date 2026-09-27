from app.invoices import invoice_block
from app.schemas import INVOICE_SCHEMA


def test_invoice_block_references_the_uploaded_file():
    block = invoice_block("file_abc")
    assert block["type"] == "document"
    assert block["source"] == {"type": "file", "file_id": "file_abc"}


def test_schema_requires_every_property():
    assert set(INVOICE_SCHEMA["required"]) == set(INVOICE_SCHEMA["properties"])
