from app import audit


def test_model_is_pinned():
    assert audit.MODEL.startswith("claude-")
