"""Claude Code's sign-in (#52), from `claude auth status`."""
import json
import subprocess

from thechatplace import signin


def _run(stdout="", error=None, seen=None):
    def run(command, **kwargs):
        assert command[1:] == ["auth", "status", "--json"]
        if seen is not None:
            seen.update(kwargs)
        if error:
            raise error
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")
    return run


def test_signed_in_to_a_subscription():
    out = json.dumps({"loggedIn": True, "authMethod": "claude.ai", "subscriptionType": "pro",
                      "email": "k@example.com"})
    status = signin.check("claude", run=_run(out))
    assert status.known and status.signed_in and status.subscription
    assert signin.describe(status) == ("Claude Code is signed in to your Claude Pro plan as "
                                       "k@example.com.")


def test_not_signed_in_api_keys_and_no_answer():
    status = signin.check("claude", run=_run(json.dumps({"loggedIn": False})))
    assert status.known and not status.signed_in
    assert signin.describe(status).startswith("Claude Code isn't signed in.")
    key = signin.check("claude", run=_run(json.dumps({"loggedIn": True,
                                                       "authMethod": "api_key"})))
    assert signin.describe(key).startswith(
        "Claude Code is set up to use an Anthropic API key, not a Claude subscription.")
    for run in (_run("not json"), _run(error=OSError("gone")),
                _run(error=subprocess.TimeoutExpired("claude", 20))):
        status = signin.check("claude", run=run)
        assert not status.known
        assert signin.describe(status).startswith("Couldn't tell whether Claude Code is signed in")


def test_asked_with_the_environment_turns_get(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-for-other-tools")
    seen = {}
    signin.check("claude", run=_run(json.dumps({"loggedIn": True}), seen=seen))
    assert "ANTHROPIC_API_KEY" not in seen["env"]
    assert seen["encoding"] == "utf-8"


def test_other_ways_of_signing_in_are_named():
    token = signin.SignIn(True, True, "oauth_token")
    assert token.subscription
    assert signin.describe(token) == ("Claude Code is using a long-lived token from your "
                                      "Claude subscription.")
    bedrock = signin.SignIn(True, True, "third_party", provider="bedrock")
    assert "Amazon Bedrock" in signin.describe(bedrock)
    nobody = signin.SignIn(True, signed_in=False, method="none")
    assert signin.describe(nobody).startswith("Claude Code isn't signed in.")
    assert signin.login_command("claude") == ["claude", "auth", "login", "--claudeai"]
