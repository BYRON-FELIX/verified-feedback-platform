#!/usr/bin/env python3
import os
import sys

import environ

if len(sys.argv) < 3:
    raise SystemExit("Usage: with-env.py ENV_FILE COMMAND [ARG ...]")

environ.Env.read_env(sys.argv[1], overwrite=True)
os.execvpe(sys.argv[2], sys.argv[2:], os.environ)
