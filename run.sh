#!/bin/bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip > /dev/null
pip install -r requirements.txt > /dev/null

if [ "$1" = "install" ] && [ -n "$2" ]; then
  pip install "$2"
  pip freeze > requirements.txt
elif [[ "$1" == *iroha* ]]; then
  # iroha 実行時は型チェックする
  python -m mypy iroha
  if [ $? -ne 0 ]; then deactivate; exit 1; fi
  python "$@"
elif [ -n "$1" ]; then
  python "$@"
else
  python -m mypy iroha
  if [ $? -ne 0 ]; then deactivate; exit 1; fi
  python iroha
fi

deactivate
