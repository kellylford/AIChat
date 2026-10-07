#!/bin/bash
# Double-click in Finder to run build_macos.sh; the window stays open to read
# the result.
cd "$(dirname "$0")" || exit 1
./build_macos.sh
status=$?
read -r -p "Press Enter to close..."
exit $status
