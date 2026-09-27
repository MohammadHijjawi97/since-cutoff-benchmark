from app.labeler import LABELS


def test_labels_are_lowercase():
    assert all(label == label.lower() for label in LABELS)
