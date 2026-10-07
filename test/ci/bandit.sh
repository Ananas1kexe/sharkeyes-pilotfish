#!/usr/bin/env bash

echo "start ==> bandit check"
cd ../..
bandit -r . -x ./.venv,./test,./scripts
echo "finish bandit check with exit code: $?"
