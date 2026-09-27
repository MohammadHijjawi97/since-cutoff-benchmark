"""Query rewriting for the search bot."""

from openai import OpenAI

MODEL = "gpt-5.5-mini"
REWRITE_INSTRUCTIONS = "Rewrite the user's question as a short web-search query. Answer with the query only."


def rewrite_query(client: OpenAI, question: str) -> str:
    response = client.responses.create(
        model=MODEL,
        instructions=REWRITE_INSTRUCTIONS,
        input=question,
        max_output_tokens=32,
    )
    return response.output_text.strip()
