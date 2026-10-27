"""Storage safety: keys from the browser must never escape the data folder."""

import pytest

from throws import TrialMeta, repository


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(repository, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(repository, "RAW_DIR", str(tmp_path / "raw"))
    monkeypatch.setattr(repository, "META_PATH", str(tmp_path / "meta.json"))
    return tmp_path


@pytest.mark.parametrize("key", ["../outside", "..\\outside", "a/b", "", "x.txt"])
def test_invalid_keys_are_rejected(store, key):
    with pytest.raises(ValueError):
        repository.load_trial(key)
    with pytest.raises(ValueError):
        repository.delete_trials([key])


def test_rejected_delete_removes_nothing(store):
    victim = store / "victim.txt"
    victim.write_text("keep")
    with pytest.raises(ValueError):
        repository.delete_trials(["../victim"])
    assert victim.exists()


def test_update_metas_writes_all_in_one_go(store):
    (store / "raw").mkdir()
    for key in ("a-1", "b_2"):
        (store / "raw" / f"{key}.txt").write_text("")
    repository.update_metas([TrialMeta(athlete="A", key="a-1"), TrialMeta(athlete="B", key="b_2")])
    assert [m.athlete for m in repository.list_metas()] == ["A", "B"]
    assert not (store / "meta.json.tmp").exists()
