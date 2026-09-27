from types import SimpleNamespace

from app.hub import model_summary, weight_files
from app.network import logger


class FakeApi:
    def model_info(self, repo_id):
        return SimpleNamespace(id=repo_id, sha="abc123", downloads=42)

    def list_repo_files(self, repo_id):
        return ["config.json", "model-00002-of-00002.safetensors", "model-00001-of-00002.safetensors", "README.md"]


def test_model_summary():
    assert model_summary("acme-ml/ner-large", api=FakeApi()) == {"id": "acme-ml/ner-large", "sha": "abc123",
                                                                 "downloads": 42}


def test_weight_files():
    assert weight_files("acme-ml/ner-large", api=FakeApi()) == ["model-00001-of-00002.safetensors",
                                                                "model-00002-of-00002.safetensors"]


def test_network_logger_name():
    assert logger.name == "app.network"
