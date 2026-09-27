"""Record formats shared with the ledger import job."""

# One row of the ledger import. The import job rejects rows with missing or extra keys.
INVOICE_SCHEMA = {
    "type": "object",
    "properties": {
        "invoice_number": {"type": "string"},
        "vendor": {"type": "string"},
        "issue_date": {"type": "string", "description": "ISO 8601 date, e.g. 2026-09-01"},
        "currency": {"type": "string", "description": "ISO 4217 code, e.g. EUR"},
        "total": {"type": "number", "description": "Amount due including tax"},
    },
    "required": ["invoice_number", "vendor", "issue_date", "currency", "total"],
    "additionalProperties": False,
}
