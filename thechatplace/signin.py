"""Whether Claude Code is signed in (#52), from ``claude auth status``.

That command answers in JSON, at once and at no cost:
``{"loggedIn": true, "authMethod": "claude.ai", "subscriptionType": "max",
"email": …, "orgName": …}``. Sessions on disk are listed either way; only
sending needs a sign-in. Signing in is ``claude auth login``, which opens
the browser, so it runs in its own window.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import List, Optional

from . import platform_paths
from .claude_cli import child_environment

_PLANS = {"max": "Max", "pro": "Pro", "team": "Team", "enterprise": "Enterprise"}
_PROVIDERS = {"bedrock": "Amazon Bedrock", "vertex": "Google Vertex AI",
              "foundry": "Microsoft Foundry"}


@dataclass
class SignIn:
    known: bool  # False when Claude Code couldn't be asked
    signed_in: bool = False
    method: str = ""  # "claude.ai" for a Claude subscription
    provider: str = ""  # "firstParty", or "bedrock" and the like
    plan: str = ""
    email: str = ""
    problem: str = ""
    missing: bool = False  # no claude it can use at all: offer to install one
    install_help: str = ""  # with ``missing``, the install commands

    @property
    def subscription(self) -> bool:
        """A Claude subscription: a sign-in, or a long-lived token made from
        one (``claude setup-token``)."""
        return self.method in ("claude.ai", "oauth_token")


def check(executable: Optional[str] = None, run=subprocess.run) -> SignIn:
    if not executable:
        lookup = platform_paths.find_claude()
        if not lookup.path:
            return SignIn(False, missing=True, problem=lookup.reason,
                          install_help=lookup.install_help)
        executable = lookup.path
    try:
        # The environment turns get: an API key or cloud provider set for
        # other tools is removed there, so it mustn't count here either.
        out = run([executable, "auth", "status", "--json"], capture_output=True, text=True,
                  encoding="utf-8", errors="replace", timeout=20,
                  env=child_environment(),
                  creationflags=platform_paths.hidden_window_flags())
    except subprocess.TimeoutExpired:
        return SignIn(False, problem=f"Claude Code ({executable}) didn't answer in 20 seconds")
    except (OSError, subprocess.SubprocessError) as exc:
        return SignIn(False, problem=f"Claude Code ({executable}) couldn't be started: {exc}")
    try:
        data = json.loads(out.stdout or "")
    except ValueError:
        return SignIn(False, problem=_no_answer(executable, out))
    if not isinstance(data, dict):
        return SignIn(False, problem="Claude Code's answer wasn't understood")
    return SignIn(True, signed_in=bool(data.get("loggedIn")),
                  method=str(data.get("authMethod") or ""),
                  provider=str(data.get("apiProvider") or ""),
                  plan=str(data.get("subscriptionType") or ""),
                  email=str(data.get("email") or ""))


def _no_answer(executable: str, out) -> str:
    """Why ``claude auth status`` gave no JSON, from what it printed.
    A version from before ``auth status`` existed says "unknown command"."""
    said = next((line.strip() for line in (out.stderr or out.stdout or "").splitlines()
                 if line.strip()), "")
    if "unknown" in said.lower() and ("command" in said.lower() or "option" in said.lower()):
        return (f"Claude Code ({executable}) is too old to say. Update it by running "
                "claude update in a terminal, then try again")
    if said:
        return f"Claude Code ({executable}) said \"{said[:200]}\""
    return f"Claude Code ({executable}) gave no answer (exit code {out.returncode})"


def describe(status: SignIn) -> str:
    if status.missing:
        return "\n\n".join(part for part in (status.problem, status.install_help) if part)
    if not status.known:
        return f"Couldn't tell whether Claude Code is signed in: {status.problem}."
    if not status.signed_in:
        return ("Claude Code isn't signed in. Your sessions still show, but sending a message "
                "needs you to sign in.")
    who = f" as {status.email}" if status.email else ""
    if status.method == "oauth_token":
        return "Claude Code is using a long-lived token from your Claude subscription."
    if status.subscription:
        plan = _PLANS.get(status.plan.lower(), "")
        plan = f"your Claude {plan} plan" if plan else "your Claude subscription"
        return f"Claude Code is signed in to {plan}{who}."
    if status.method == "third_party":
        how = _PROVIDERS.get(status.provider.lower(), "a cloud provider")
    elif status.method == "api_key":
        how = "an Anthropic API key"
    else:
        how = "something other than your Claude account"
    return (f"Claude Code is set up to use {how}, not a Claude subscription. The Chat Place "
            "only runs turns on a subscription, so sign in with your Claude account.")


def login_command(executable: Optional[str] = None) -> Optional[List[str]]:
    executable = executable or platform_paths.claude_executable()
    return [executable, "auth", "login", "--claudeai"] if executable else None
