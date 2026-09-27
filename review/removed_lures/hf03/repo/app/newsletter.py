"""The "around the Hub" section of the monthly newsletter."""

from huggingface_hub import HfApi

WATCHED_FAMILIES = ("whisper", "parakeet", "wav2vec2")


def popular_variants(family: str, limit: int = 5) -> list[str]:
    """Public models named after `family` (fine-tunes, distillations, ports), most liked first."""
    return [m.id for m in HfApi().list_models(model_name=family, sort="likes", limit=limit)]


def newsletter_section() -> str:
    lines = []
    for family in WATCHED_FAMILIES:
        lines.append(f"## {family}")
        lines.extend(f"- https://huggingface.co/{repo_id}" for repo_id in popular_variants(family))
    return "\n".join(lines)
