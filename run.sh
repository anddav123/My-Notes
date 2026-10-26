#!/bin/sh
# Run from any directory, with the tested project dependencies.
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if [ ! -x .venv/bin/python ]; then
    printf '%s\n' 'Set up the project environment first; see README.md.' >&2
    exit 1
fi
exec .venv/bin/python main.py "$@"
