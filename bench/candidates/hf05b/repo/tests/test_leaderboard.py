from types import SimpleNamespace

from app.leaderboard import model_link, org_model_count


class FakeApi:
    def list_models(self, **kwargs):
        assert kwargs == {"author": "acme"}
        return iter([SimpleNamespace(id="acme/a"), SimpleNamespace(id="acme/b")])


def test_model_link():
    assert model_link("acme/bert") == "https://huggingface.co/acme/bert"


def test_org_model_count():
    assert org_model_count("acme", api=FakeApi()) == 2
