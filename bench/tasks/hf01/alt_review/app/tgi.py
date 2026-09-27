"""Client for our self-hosted TGI endpoint.

Reviewer's alternative answer: the endpoint given as `base_url`, and `return_full_text=False` spelled out.
"""

from huggingface_hub import InferenceClient


def complete_paragraph(endpoint_url: str, prompt: str) -> str:
    client = InferenceClient(base_url=endpoint_url)
    out = client.text_generation(prompt, max_new_tokens=200, stop=["\n\n"], return_full_text=False)
    return out.rstrip()
