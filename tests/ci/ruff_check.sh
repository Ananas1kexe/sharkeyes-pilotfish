#!/usr/bin/env bash

cd ../..
ruff check --fix .
echo "finish ruff check with exit code: $?"