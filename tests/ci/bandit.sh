#!/usr/bin/env bash

cd ../..
bandit -r . -x ./.venv,./test,./scripts
echo "finish bandit check with exit code: $?"
