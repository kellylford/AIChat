"""Attaching files and images to a message (#22)."""
import base64
import json

from thechatplace import attachments, platform_paths
from thechatplace.claude_cli import stdin_lines
from markers import windows_paths  # noqa: E402

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=")


def test_images_go_inline_and_files_as_quoted_mentions(tmp_path):
    image = tmp_path / "shot one.png"
    image.write_bytes(PNG)
    note = tmp_path / "my notes.txt"
    note.write_text("hi", encoding="utf-8")
    text, blocks = attachments.build("Look at these", [str(image), str(note)])
    assert text == f'Look at these\n\nAttached: @"{note}"'
    assert blocks == [{"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                   "data": base64.b64encode(PNG).decode()}}]


def test_queued_messages_and_big_images_use_mentions(tmp_path, monkeypatch):
    image = tmp_path / "a.png"
    image.write_bytes(PNG)
    text, blocks = attachments.build("", [str(image)], images_inline=False)
    assert blocks == [] and text == f'Attached: @"{image}"'
    monkeypatch.setattr(attachments, "MAX_IMAGE_BYTES", 10)
    text, blocks = attachments.build("big", [str(image)])
    assert blocks == [] and f'@"{image}"' in text


def test_a_file_that_is_gone_is_said_not_sent(tmp_path):
    text, blocks = attachments.build("hi", [str(tmp_path / "gone.txt")])
    assert text == "hi\n\n(Couldn't attach, no longer there: gone.txt)" and blocks == []


@windows_paths
def test_describe_and_media_types():
    assert attachments.describe([]) == "No attachments"
    assert attachments.describe(["C:\\x\\a.png", "C:\\y\\b.txt"]) == "2 attachments: a.png, b.txt"
    assert attachments.media_type("x.JPG") == "image/jpeg"
    assert attachments.media_type("x.pdf") is None


def test_pasted_images_get_their_own_names(tmp_path, monkeypatch):
    monkeypatch.setattr(platform_paths, "app_data_dir", lambda: tmp_path)
    first = attachments.pasted_image_path(when=0)
    first.parent.mkdir(parents=True)
    first.write_bytes(PNG)
    second = attachments.pasted_image_path(when=0)
    assert first.name.startswith("Pasted image ") and second.name.endswith(" (2).png")
    assert first.parent == tmp_path / "pasted images"


def test_the_message_carries_image_blocks_after_its_text():
    block = {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                         "data": "x"}}
    lines = stdin_lines("Describe", [block]).decode("utf-8").splitlines()
    message = json.loads(lines[1])["message"]
    assert message["content"] == [{"type": "text", "text": "Describe"}, block]
    assert json.loads(stdin_lines("plain").decode().splitlines()[1])["message"]["content"] == "plain"


def test_image_type_comes_from_the_file_not_its_name(tmp_path):
    jpeg_named_png = tmp_path / "photo.png"
    jpeg_named_png.write_bytes(b"\xff\xd8\xff\xe0" + b"0" * 20)
    text_named_png = tmp_path / "not really.png"
    text_named_png.write_text("hello", encoding="utf-8")
    text, blocks = attachments.build("", [str(jpeg_named_png), str(text_named_png)])
    assert [b["source"]["media_type"] for b in blocks] == ["image/jpeg"]
    assert text == f'Attached: @"{text_named_png}"'  # not an image: Claude Code reads it


def test_the_limit_counts_the_encoded_size():
    assert attachments.fits_inline(3 * 1024 * 1024)
    assert not attachments.fits_inline(4 * 1024 * 1024)  # under 5 MB raw, over once encoded
    assert attachments.fits_inline(attachments.MAX_IMAGE_BYTES * 3 // 4)


def test_old_pasted_pictures_are_removed(tmp_path, monkeypatch):
    import os
    monkeypatch.setattr(platform_paths, "app_data_dir", lambda: tmp_path)
    folder = attachments.paste_folder()
    folder.mkdir(parents=True)
    old = folder / "Pasted image old.png"
    new = folder / "Pasted image new.png"
    keep = folder / "mine.png"  # not ours by name: left alone
    for path in (old, new, keep):
        path.write_bytes(PNG)
    os.utime(old, (1, 1))
    os.utime(keep, (1, 1))
    assert attachments.remove_old_pastes(days=30) == 1
    assert not old.exists() and new.exists() and keep.exists()
