from app import limits, worker


def test_worker_shares_the_cli_settings():
    assert worker.MODEL == limits.MODEL
    assert worker.TOKENS_REMAINING == "anthropic-ratelimit-tokens-remaining"


def test_low_watermark_is_positive():
    assert worker.LOW_WATERMARK > 0
