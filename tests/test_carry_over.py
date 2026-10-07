"""TheClaudeHub's data comes along to The Chat Place, once (#25)."""
import shutil

from thechatplace import app, platform_paths


def _old(tmp_path):
    old = tmp_path / "TheClaudeHub"
    (old / "pasted images").mkdir(parents=True)
    (old / "pasted images" / "a.png").write_bytes(b"png")
    (old / "sessions.json").write_text('{"old": 1}', encoding="utf-8")
    (old / "groups.json").write_text('{"IDT": []}', encoding="utf-8")
    (old / "speech.json").write_text("{}", encoding="utf-8")
    (old / "update.log").write_text("log", encoding="utf-8")
    return old


def test_copied_once_never_replacing_and_the_old_folder_kept(tmp_path):
    old = _old(tmp_path)
    new = tmp_path / "TheChatPlace"
    new.mkdir()
    (new / "speech.json").write_text('{"new": 1}', encoding="utf-8")  # already here: kept
    assert platform_paths.carry_over_old_data(tmp_path) == []
    assert (new / "sessions.json").read_text(encoding="utf-8") == '{"old": 1}'
    assert (new / "groups.json").read_text(encoding="utf-8") == '{"IDT": []}'
    assert (new / "speech.json").read_text(encoding="utf-8") == '{"new": 1}'
    assert (new / "pasted images" / "a.png").read_bytes() == b"png"
    assert not (new / "update.log").exists()
    assert not list(new.glob("*.carrying"))
    assert (old / "sessions.json").exists()  # copied, not moved
    # Only once: a session forgotten since isn't brought back.
    (new / "sessions.json").unlink()
    assert platform_paths.carry_over_old_data(tmp_path) == []
    assert not (new / "sessions.json").exists()


def test_a_copy_cut_short_is_finished_next_time(tmp_path, monkeypatch):
    _old(tmp_path)
    new = tmp_path / "TheChatPlace"
    real = shutil.copytree

    def fails(source, target, *args, **kwargs):
        real(source, target, *args, **kwargs)
        raise shutil.Error([("a.png", "b", "locked")])
    monkeypatch.setattr(platform_paths.shutil, "copytree", fails)
    problems = platform_paths.carry_over_old_data(tmp_path)
    assert problems and problems[0].startswith("pasted images")
    assert not (new / "pasted images").exists()  # no half folder taken for whole
    assert (new / "sessions.json").exists()      # what did come across stays
    assert not (new / platform_paths._CARRIED_OVER).exists()  # so: again next start
    monkeypatch.setattr(platform_paths.shutil, "copytree", real)
    assert platform_paths.carry_over_old_data(tmp_path) == []
    assert (new / "pasted images" / "a.png").exists()


def test_nothing_to_carry_over(tmp_path):
    assert platform_paths.carry_over_old_data(tmp_path) == []
    assert not (tmp_path / "TheChatPlace").exists()


def test_a_smoke_test_never_carries_over(tmp_path, monkeypatch):
    def never(*args, **kwargs):
        raise AssertionError("carried over for a smoke test")
    monkeypatch.setattr(platform_paths, "carry_over_old_data", never)
    monkeypatch.setattr(app, "smoke_test", lambda target: 0)
    assert app.main(["--smoke-test", str(tmp_path / "s.json")]) == 0
