"""TheClaudeHub's data comes along to The Chat Place, once (#25)."""
from thechatplace import platform_paths


def test_copied_once_never_replacing_and_the_old_folder_kept(tmp_path):
    old = tmp_path / "TheClaudeHub"
    (old / "pasted images").mkdir(parents=True)
    (old / "pasted images" / "a.png").write_bytes(b"png")
    (old / "sessions.json").write_text('{"old": 1}', encoding="utf-8")
    (old / "speech.json").write_text("{}", encoding="utf-8")
    (old / "update.log").write_text("log", encoding="utf-8")
    new = tmp_path / "TheChatPlace"
    new.mkdir()
    (new / "speech.json").write_text('{"new": 1}', encoding="utf-8")  # already here: kept
    copied = platform_paths.carry_over_old_data(tmp_path)
    assert sorted(copied) == ["pasted images", "sessions.json"]
    assert (new / "sessions.json").read_text(encoding="utf-8") == '{"old": 1}'
    assert (new / "speech.json").read_text(encoding="utf-8") == '{"new": 1}'
    assert (new / "pasted images" / "a.png").read_bytes() == b"png"
    assert not (new / "update.log").exists()
    assert (old / "sessions.json").exists()  # copied, not moved
    # Only once: a session forgotten since isn't brought back.
    (new / "sessions.json").unlink()
    assert platform_paths.carry_over_old_data(tmp_path) == []
    assert not (new / "sessions.json").exists()


def test_nothing_to_carry_over(tmp_path):
    assert platform_paths.carry_over_old_data(tmp_path) == []
    assert not (tmp_path / "TheChatPlace").exists()
