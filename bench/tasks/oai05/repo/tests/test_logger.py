from app.llm_client import logger


def test_logger_name():
    assert logger.name == "app.http"
