"""Other machines (#123): the ListAgents list and the send prompt.

The list text is made up but shaped like Claude Code 2.1.286's ListAgents
output; no real session names or content.
"""
from thechatplace import remote

LISTING = """This session is test-project-36 [4f2aaa] - the name other sessions use to message it.

Peer sessions (5):
  Surface Hub [66e038]  ·  Remote Control  ·  offline
  Mac work [a03676]  ·  Remote Control  ·  requires_action
  Local helper [123abc]  ·  Claude Desktop session  ·  idle
  Fix [the] thing [8a038b]  ·  Remote Control
  Surface Hub [9ba6e5]  ·  Remote Control  ·  idle
not a row at all
  Broken [zz]  ·  Remote Control  ·  idle
"""


def test_parse_keeps_remote_control_rows_in_order():
    sessions = remote.parse_list(LISTING)
    assert [(s.name, s.ref, s.state) for s in sessions] == [
        ("Surface Hub", "66e038", "offline"),
        ("Mac work", "a03676", "requires_action"),
        ("Fix [the] thing", "8a038b", ""),
        ("Surface Hub", "9ba6e5", "idle")]
    assert sessions[0].describe() == "Surface Hub, offline"
    assert sessions[1].describe() == "Mac work, needs you"
    assert remote.spoken_state("some_new_state") == "some new state"
    assert sessions[2].describe() == "Fix [the] thing"


def test_shared_names_get_their_ref_in_the_address():
    sessions = remote.parse_list(LISTING)
    assert remote.addresses(sessions) == [
        "Surface Hub [66e038]", "Mac work", "Fix [the] thing", "Surface Hub [9ba6e5]"]


def test_parse_survives_nonsense():
    assert remote.parse_list("") == []
    assert remote.parse_list(None) == []
    assert remote.parse_list("No peer sessions.\n\x00\n[abc] · ·") == []


def test_latest_list_uses_the_newest_listagents_result():
    results = ["Bash returned: ok",
               "ListAgents returned: Peer sessions (1):\n  Old [111111]  ·  Remote Control  ·  idle",
               "Read returned: x",
               "ListAgents returned: Peer sessions (1):\n  New [222222]  ·  Remote Control  ·  idle"]
    assert [s.name for s in remote.latest_list(results)] == ["New"]
    assert remote.latest_list(["Bash returned: ok"]) is None
    assert remote.latest_list(["ListAgents returned: Peer sessions (0):"]) == []


def test_send_prompt_carries_the_words_exactly():
    prompt = remote.send_prompt('Surface  "Hub"\n[66e038]', "  Line one\n---\nLine two  ")
    assert '"Surface \'Hub\' [66e038]"' in prompt
    assert prompt.endswith("<<<MESSAGE\nLine one\n---\nLine two\nMESSAGE>>>")
    assert "SendMessage" in prompt and "exactly as written" in prompt
    assert "ListAgents" in remote.LIST_PROMPT and "Don't send" in remote.LIST_PROMPT
