"""View, Links (#190): finding the links in a session's messages."""
import pytest

from thechatplace.message_links import FoundLink, find_links, links_in_text, matches
from thechatplace.transcript import ASSISTANT, USER, ChatMessage


def msg(kind, text):
    return ChatMessage(kind, text)


def test_markdown_angle_and_bare_links_in_order():
    text = ("See the [release notes](https://github.com/o/r/releases/tag/v1), "
            "<https://example.com/a> and https://docs.example.com/x.")
    assert links_in_text(text) == [
        ("https://github.com/o/r/releases/tag/v1", "release notes", False),
        ("https://example.com/a", "", False),
        ("https://docs.example.com/x", "", False),
    ]


@pytest.mark.parametrize("text, url", [
    ("(see https://x.org/a).", "https://x.org/a"),
    ("https://en.wikipedia.org/wiki/Foo_(bar), then", "https://en.wikipedia.org/wiki/Foo_(bar)"),
    ("**https://x.org/b**", "https://x.org/b"),
    ("Done: https://x.org/c?q=1&r=2!", "https://x.org/c?q=1&r=2"),
    ("[Foo](https://en.wikipedia.org/wiki/Foo_(bar))", "https://en.wikipedia.org/wiki/Foo_(bar)"),
    ('[t](https://x.org/d "Title")', "https://x.org/d"),
])
def test_addresses_end_where_they_should(text, url):
    assert links_in_text(text)[0][0] == url


def test_links_in_code_are_marked_and_markdown_in_code_is_not_a_link():
    text = ("Run:\n```bash\ncurl https://api.example.com/v1 [x](https://not.md/)\n```\n"
            "and `open https://inline.example.com` too.")
    found = links_in_text(text)
    assert ("https://api.example.com/v1", "", True) in found
    assert ("https://inline.example.com", "", True) in found
    # Inside a code block, [x](…) is code: only the bare address is found.
    assert all(words == "" for _url, words, _code in found)


def test_words_that_are_the_address_again_read_as_the_address():
    assert links_in_text("[https://x.org/a](https://x.org/a)") == [("https://x.org/a", "", False)]
    assert links_in_text("[x.org/a](https://x.org/a)") == [("https://x.org/a", "", False)]


def test_find_links_is_newest_first_once_each_with_who_and_when():
    messages = [msg(USER, "Look at https://a.org/one"),
                msg(ASSISTANT, "Sure: [the doc](https://b.org/doc) and https://a.org/one"),
                msg(USER, "thanks"),
                msg(ASSISTANT, "Also https://c.org/")]
    found = find_links(messages)
    # Newest message first; within a message, in the order they're written.
    assert [f.url for f in found] == ["https://c.org/", "https://b.org/doc", "https://a.org/one"]
    assert found[0].row() == "c.org/. Claude, the latest message"
    assert found[1].row() == "the doc, b.org/doc. Claude, 2 messages ago"
    assert found[2].row() == "a.org/one. Claude, 2 messages ago"
    assert found[2].ago == 2 and found[2].who == "Claude"


def test_a_repeated_address_keeps_words_from_an_older_mention():
    messages = [msg(ASSISTANT, "[release notes](https://x.org/r)"),
                msg(USER, "https://x.org/r")]
    (link,) = find_links(messages)
    assert link.words == "release notes" and link.who == "You" and link.ago == 0


def test_only_web_mail_and_session_links_open():
    web = FoundLink("https://x.org", "", "Claude", 0)
    mail = FoundLink("mailto:me@x.org", "", "Claude", 1)
    session = FoundLink("thechatplace://session/abc-1", "Build", "You", 2)
    file_link = FoundLink("file:///C:/secret.txt", "notes", "Claude", 0)
    script = FoundLink("javascript:alert(1)", "click", "Claude", 0)
    bad_app = FoundLink("thechatplace://elsewhere/x", "", "Claude", 0)
    assert web.can_open and mail.can_open and session.can_open
    assert not file_link.can_open and not script.can_open and not bad_app.can_open
    assert mail.address == "me@x.org"
    assert file_link.why_not().startswith("A file: link isn't opened from here")
    assert "copy only" in script.row()
    assert bad_app.why_not().startswith("That link isn't one The Chat Place knows.")
    assert web.why_not() == ""


def test_markdown_copy():
    assert FoundLink("https://x.org", "a [b]", "Claude", 0).markdown() == "[a \\[b\\]](https://x.org)"
    assert FoundLink("https://x.org", "", "Claude", 0).markdown() == "<https://x.org>"


def test_filter_matches_every_word():
    link = FoundLink("https://github.com/o/r", "release notes", "Claude", 0)
    assert matches(link, "release github")
    assert matches(link, "CLAUDE")
    assert not matches(link, "release gitlab")


def test_no_links_and_odd_text():
    assert find_links([msg(USER, ""), msg(ASSISTANT, "No links here. Not http:// either.")]) == []
    assert links_in_text("an email: someone@example.com") == []
    assert links_in_text("ftp://x.org isn't web") == []
