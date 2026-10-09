"""A stand-in for the GitHub CLI (#154), for tests.

``repo list ... --json ...`` prints FAKE_GH_REPOS (JSON) or fails with
FAKE_GH_FAIL. ``repo clone owner/name folder`` makes the folder as a git
repository whose origin is github.com/owner/name; FAKE_GH_MODE=hang starts it
and then waits, so a test can cancel it; FAKE_GH_MODE=fail fails.
"""
import os
import subprocess
import sys
import time

args = sys.argv[1:]
mode = os.environ.get("FAKE_GH_MODE", "")
if args[:2] == ["repo", "list"]:
    if os.environ.get("FAKE_GH_FAIL"):
        sys.stderr.write(os.environ["FAKE_GH_FAIL"] + "\n")
        sys.exit(1)
    print(os.environ.get("FAKE_GH_REPOS", "[]"))
    sys.exit(0)
if args[:2] == ["repo", "clone"]:
    repo, folder = args[2], args[3]
    if mode == "fail":
        sys.stderr.write(f"GraphQL: Could not resolve to a Repository with the name '{repo}'.\n")
        sys.exit(1)
    os.makedirs(folder)
    subprocess.run(["git", "init", "-q", folder], check=True)
    subprocess.run(["git", "-C", folder, "remote", "add", "origin",
                    f"https://github.com/{repo}.git"], check=True)
    if mode == "hang":
        time.sleep(60)
    sys.exit(0)
sys.stderr.write(f"fake gh: unknown command {args}\n")
sys.exit(2)
