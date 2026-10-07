"""Claude Code's sign-in (#52), from `claude auth status`."""
import json
import subprocess

from theclaudehub import signin


def _run(stdout="", error=None):
    def run(command, **kwargs):
        assert command[1:] == ["auth", "status", "--json"]
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
    assert "not a Claude subscription" in signin.describe(key)
    for run in (_run("not json"), _run(error=OSError("gone")),
                _run(error=subprocess.TimeoutExpired("claude", 20))):
        status = signin.check("claude", run=run)
        assert not status.known
        assert signin.describe(status).startswith("Couldn't tell whether Claude Code is signed in")
