#!/bin/bash
# Double-click in Finder to run macsetup.sh, as in Image Description Toolkit.
cd "$(dirname "$0")" || exit 1
exec ./macsetup.sh
