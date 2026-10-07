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

    @property
    def subscription(self) -> bool:
        """A Claude subscription: a sign-in, or a long-lived token made from
        one (``claude setup-token``)."""
        return self.method in ("claude.ai", "oauth_token")


def check(executable: Optional[str] = None, run=subprocess.run) -> SignIn:
    executable = executable or platform_paths.claude_executable()
    if not executable:
        return SignIn(False, problem="Claude Code isn't installed, or TheClaudeHub can't find it")
    try:
        # The environment turns get: an API key or cloud provider set for
        # other tools is removed there, so it mustn't count here either.
        out = run([executable, "auth", "status", "--json"], capture_output=True, text=True,
                  encoding="utf-8", errors="replace", timeout=20,
                  env=child_environment(),
                  creationflags=platform_paths.hidden_window_flags())
        data = json.loads(out.stdout or "")
    except (OSError, subprocess.SubprocessError, ValueError):
        return SignIn(False, problem="Claude Code didn't answer")
    if not isinstance(data, dict):
        return SignIn(False, problem="Claude Code's answer wasn't understood")
    return SignIn(True, signed_in=bool(data.get("loggedIn")),
                  method=str(data.get("authMethod") or ""),
                  provider=str(data.get("apiProvider") or ""),
                  plan=str(data.get("subscriptionType") or ""),
                  email=str(data.get("email") or ""))


def describe(status: SignIn) -> str:
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
    return (f"Claude Code is set up to use {how}, not a Claude subscription. TheClaudeHub "
            "only runs turns on a subscription, so sign in with your Claude account.")


def login_command(executable: Optional[str] = None) -> Optional[List[str]]:
    executable = executable or platform_paths.claude_executable()
    return [executable, "auth", "login", "--claudeai"] if executable else None
