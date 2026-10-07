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

_PLANS = {"max": "Max", "pro": "Pro", "team": "Team", "enterprise": "Enterprise"}


@dataclass
class SignIn:
    known: bool  # False when Claude Code couldn't be asked
    signed_in: bool = False
    method: str = ""  # "claude.ai" for a Claude subscription
    plan: str = ""
    email: str = ""
    problem: str = ""

    @property
    def subscription(self) -> bool:
        return self.method == "claude.ai"


def check(executable: Optional[str] = None, run=subprocess.run) -> SignIn:
    executable = executable or platform_paths.claude_executable()
    if not executable:
        return SignIn(False, problem="Claude Code isn't installed, or TheClaudeHub can't find it")
    try:
        out = run([executable, "auth", "status", "--json"], capture_output=True, text=True,
                  timeout=20, creationflags=platform_paths.hidden_window_flags())
        data = json.loads(out.stdout or "")
    except (OSError, subprocess.SubprocessError, ValueError):
        return SignIn(False, problem="Claude Code didn't answer")
    if not isinstance(data, dict):
        return SignIn(False, problem="Claude Code's answer wasn't understood")
    return SignIn(True, signed_in=bool(data.get("loggedIn")),
                  method=str(data.get("authMethod") or ""),
                  plan=str(data.get("subscriptionType") or ""),
                  email=str(data.get("email") or ""))


def describe(status: SignIn) -> str:
    if not status.known:
        return f"Couldn't tell whether Claude Code is signed in: {status.problem}."
    if not status.signed_in:
        return ("Claude Code isn't signed in. Your sessions still show, but sending a message "
                "needs you to sign in.")
    who = f" as {status.email}" if status.email else ""
    if status.subscription:
        plan = _PLANS.get(status.plan.lower(), "")
        plan = f"your Claude {plan} plan" if plan else "your Claude subscription"
        return f"Claude Code is signed in to {plan}{who}."
    return (f"Claude Code is signed in{who} with {status.method or 'another method'}, not a "
            "Claude subscription. TheClaudeHub only runs turns on a subscription, so sign in "
            "with your Claude account.")


def login_command(executable: Optional[str] = None) -> Optional[List[str]]:
    executable = executable or platform_paths.claude_executable()
    return [executable, "auth", "login"] if executable else None
