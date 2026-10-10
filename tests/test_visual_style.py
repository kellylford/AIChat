"""Colours, measured rather than looked at (#155).

The formatted view's CSS meets WCAG 2.2 AA in light and dark mode, and
keeps code blocks visible under High Contrast. The window's own controls set
no colours: they take the system's, so dark mode and High Contrast reach
them, and a hard-coded colour would stay the same in every theme.
"""
import re
from pathlib import Path

from thechatplace import rendering

UI = Path(rendering.__file__).resolve().parent / "ui"

#: What the browser uses where the CSS sets nothing (light mode): black
#: text on white, and its own link colours.
BROWSER_LIGHT = {"text": "#000000", "background": "#ffffff", "link": "#0000ee",
                 "visited": "#551a8b"}


def _channel(value: int) -> float:
    c = value / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_colour: str) -> float:
    hex_colour = hex_colour.lstrip("#")
    if len(hex_colour) == 3:
        hex_colour = "".join(ch * 2 for ch in hex_colour)
    r, g, b = (int(hex_colour[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_contrast_matches_known_values():
    assert round(contrast("#000000", "#ffffff"), 1) == 21.0
    assert round(contrast("#767676", "#ffffff"), 2) == 4.54


def _rules(css: str) -> dict:
    """selector -> {property: value}, for rules not inside an @media block."""
    rules = {}
    for selectors, body in re.findall(r"([^{}@]+)\{([^{}]*)\}", css):
        props = dict((k.strip(), v.strip()) for k, v in
                     (p.split(":", 1) for p in body.split(";") if ":" in p))
        for selector in selectors.split(","):
            rules.setdefault(selector.strip(), {}).update(props)
    return rules


def _media(css: str, query: str) -> str:
    start = css.index(f"@media ({query})")
    depth, i = 0, css.index("{", start)
    for j in range(i, len(css)):
        depth += {"{": 1, "}": -1}.get(css[j], 0)
        if depth == 0:
            return css[i + 1:j]
    raise AssertionError(f"@media ({query}) isn't closed")


def _top_level(css: str) -> str:
    return re.sub(r"@media[^{]*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}", "", css)


def _colour(value: str) -> str:
    match = re.search(r"#[0-9a-fA-F]{3,6}\b", value)
    assert match, value
    return match.group(0).lower()


def test_light_mode_text_links_and_borders_are_readable():
    rules = _rules(_top_level(rendering._STYLE))
    # Light mode leaves text and links to the browser; if that changes, this
    # test must measure the new colours instead.
    assert "color" not in rules["body"] and "a" not in rules
    pre = _colour(rules["pre"]["background"])
    for background in (BROWSER_LIGHT["background"], pre):
        for kind in ("text", "link", "visited"):
            assert contrast(BROWSER_LIGHT[kind], background) >= 4.5, (kind, background)
    border = _colour(rules["td"]["border"])
    assert contrast(border, BROWSER_LIGHT["background"]) >= 3  # WCAG 1.4.11


def test_dark_mode_text_links_and_borders_are_readable():
    light = _rules(_top_level(rendering._STYLE))
    dark = _rules(_media(rendering._STYLE, "prefers-color-scheme: dark"))
    body, pre = _colour(dark["body"]["background"]), _colour(dark["pre"]["background"])
    text = _colour(dark["body"]["color"])
    for background in (body, pre):
        assert contrast(text, background) >= 4.5
    # #102 promised 6.6:1 for links, visited ones too. On the page, that is:
    # markdown never makes a link inside a code block.
    assert contrast(_colour(dark["a"]["color"]), body) >= 6.6
    assert contrast(_colour(dark["a:visited"]["color"]), body) >= 6.6
    assert contrast(_colour(light["td"]["border"]), body) >= 3


def test_code_blocks_keep_an_edge_in_high_contrast():
    # High Contrast (forced colours) drops background colours, which is all
    # that marks a code block in the normal style, so it gets a border there
    # in the theme's own text colour.
    forced = _rules(_media(rendering._STYLE, "forced-colors: active"))
    assert "CanvasText" in forced["pre"]["border"]


def test_the_page_says_it_has_a_dark_style():
    # Without color-scheme, WebView2 draws its scroll bars and focus rings
    # for a light page even when the page is dark.
    assert _rules(_top_level(rendering._STYLE))[":root"]["color-scheme"] == "light dark"


#: A literal colour in the window's code, which would look the same in every
#: theme. A line may keep one with a comment saying why: "# colour: ...".
_LITERAL_COLOUR = re.compile(
    r"wx\.Colour\(|Set(Background|Foreground)Colour\(|SetTextForeground\(|SetTextBackground\("
    r"|wx\.(RED|GREEN|BLUE|WHITE|BLACK|LIGHT_GREY|CYAN|YELLOW)\b|[\"']#[0-9a-fA-F]{3,8}[\"']")


def test_the_window_sets_no_colours_of_its_own():
    found = []
    for path in sorted(UI.glob("*.py")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if (_LITERAL_COLOUR.search(line) and "# colour:" not in line
                    and "wx.SystemSettings" not in line):  # the theme's own colours
                found.append(f"{path.name}:{number}: {line.strip()}")
    assert found == []
