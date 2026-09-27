from types import SimpleNamespace

from app.catalog import ORG, org_models


class FakeApi:
    def __init__(self):
        self.kwargs = None

    def list_models(self, **kwargs):
        self.kwargs = kwargs
        return iter([SimpleNamespace(id=f"{ORG}/whisper-medium-de"), SimpleNamespace(id=f"{ORG}/whisper-small-nl")])


def test_org_models_lists_our_org():
    api = FakeApi()
    assert org_models(api=api) == [f"{ORG}/whisper-medium-de", f"{ORG}/whisper-small-nl"]
    assert api.kwargs["author"] == ORG
