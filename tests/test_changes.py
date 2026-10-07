"""What a turn changed in files (#18)."""
from theclaudehub.changes import by_file, edit_from_tool, file_text, summary_text
from theclaudehub.transcript import parse_lines

from records import assistant_block, lines, text_block, tool_result, tool_use_block, user_text

PATCH = [{"oldStart": 10, "oldLines": 3, "newStart": 10, "newLines": 4,
          "lines": [" keep", "-old line", "+new line", "+another", " end"]}]


def test_edit_uses_the_patch_claude_code_recorded():
    edit = edit_from_tool("Edit", {"file_path": "C:\\r\\a.py"},
                          {"filePath": "C:\\r\\a.py", "structuredPatch": PATCH}, 1)
    assert (edit.added, edit.removed, edit.created) == (2, 1, False)
    text = file_text(by_file([edit])[0])
    assert text.split("\n") == [
        "C:\\r\\a.py: 2 lines added, 1 removed.", "", "Lines 10 to 13:",
        "Unchanged: keep", "Removed: old line", "Added: new line", "Added: another",
        "Unchanged: end"]


def test_without_a_patch_the_change_comes_from_the_input():
    edit = edit_from_tool("Edit", {"file_path": "a.py", "old_string": "x = 1\ny = 2",
                                   "new_string": "x = 1\ny = 3\nz = 4"}, None, 1)
    assert (edit.added, edit.removed) == (2, 1)
    multi = edit_from_tool("MultiEdit", {"file_path": "a.py", "edits": [
        {"old_string": "a", "new_string": "b"}, {"old_string": "c", "new_string": ""}]}, None, 1)
    assert (multi.added, multi.removed) == (1, 2)
    assert "A change:" in file_text(by_file([multi])[0])
    write = edit_from_tool("Write", {"file_path": "n.txt", "content": "one\ntwo\n"},
                           {"type": "create", "filePath": "n.txt", "content": "one\ntwo\n",
                            "structuredPatch": []}, 2)
    assert write.created and write.added == 2
    assert edit_from_tool("Bash", {"command": "ls"}, None, 1) is None


def test_summary_groups_by_file_and_says_created():
    a1 = edit_from_tool("Edit", {}, {"filePath": "C:\\r\\a.py", "structuredPatch": PATCH}, 1)
    a2 = edit_from_tool("Edit", {}, {"filePath": "c:\\R\\A.py", "structuredPatch": PATCH}, 1)
    new = edit_from_tool("Write", {"file_path": "C:\\r\\new.md", "content": "x"},
                         {"type": "create"}, 1)
    gone = edit_from_tool("Edit", {"file_path": "b.py", "old_string": "x", "new_string": ""},
                          None, 1)
    assert summary_text([a1, a2, new, gone]) == (
        "Changed 3 files: a.py, 4 lines added, 2 removed; new.md, created, 1 line; "
        "b.py, 1 line removed.")
    assert summary_text([]) == ""
    many = [edit_from_tool("Write", {"file_path": f"f{i}.txt", "content": "x"}, None, 1)
            for i in range(7)]
    assert summary_text(many).endswith("; and 2 more.")


def test_transcript_keeps_successful_edits_by_turn():
    tr = parse_lines(lines(
        user_text("Fix it"),
        assistant_block(tool_use_block("Edit", {"file_path": "a.py", "old_string": "x",
                                                "new_string": "y"}, "t1"), "m1"),
        tool_result("t1", "The file a.py has been updated.",
                    toolUseResult={"filePath": "a.py", "structuredPatch": PATCH}),
        assistant_block(tool_use_block("Write", {"file_path": "b.py", "content": "z"}, "t2"),
                        "m2"),
        tool_result("t2", "File has not been read yet.", is_error=True),
        assistant_block(text_block("Done."), "m3"),
        user_text("Now the docs"),
        assistant_block(tool_use_block("Write", {"file_path": "README.md", "content": "Hi\n"},
                                       "t3"), "m4"),
        tool_result("t3", "File created.", toolUseResult={"type": "create",
                                                          "filePath": "README.md",
                                                          "content": "Hi\n",
                                                          "structuredPatch": []}),
    ))
    assert [(e.path, e.turn) for e in tr.edits] == [("a.py", 1), ("README.md", 2)]
    assert tr.turns == 2
    assert [e.path for e in tr.latest_turn_edits()] == ["README.md"]
