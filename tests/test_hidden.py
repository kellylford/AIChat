"""Hidden sessions (File, Hide Session): the store."""
import pytest

from thechatplace.hidden import HiddenStore


def test_hide_show_rename_and_kept_across_loads(tmp_path):
    path = tmp_path / "hidden.json"
    store = HiddenStore(path)
    store.hide("own:a")
    store.hide("local_b")
    store.rename_key("own:a", "own:c")
    assert HiddenStore(path).keys() == ["local_b", "own:c"]
    store.show("local_b")
    assert "local_b" not in HiddenStore(path)
    assert not list(tmp_path.glob("hidden-*.tmp"))


def test_a_bad_file_is_reported_and_never_saved_over(tmp_path):
    path = tmp_path / "hidden.json"
    path.write_text("[not ours", encoding="utf-8")
    store = HiddenStore(path)
    assert store.load_error and store.keys() == []
    with pytest.raises(OSError):
        store.hide("own:a")
    assert path.read_text(encoding="utf-8") == "[not ours"
