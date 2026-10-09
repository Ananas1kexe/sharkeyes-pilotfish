#!/usr/bin/env bash

STATUS=$?

pip-audit -r ../../requirements.txt --desc
if [ $STATUS -ne 0 ]; then
    echo "pip audit finished with error (exit code: $STATUS)"
fi
echo "pip audit finiched with exit code: $STATUS"
