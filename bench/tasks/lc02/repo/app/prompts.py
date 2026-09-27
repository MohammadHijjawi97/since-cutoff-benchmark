"""Prompt texts used by the support helpers."""

SUMMARY_PROMPT = (
    "You summarise customer support tickets for the on-call engineer. "
    "Write one sentence saying what is broken and for whom. No greeting, no sign-off."
)

TRANSLATE_PROMPT = (
    "Translate the following support reply into {language}. Keep product names, URLs and "
    "ticket numbers unchanged. Answer with the translation only.\n\n{text}"
)
