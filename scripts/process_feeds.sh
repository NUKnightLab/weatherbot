#!/usr/bin/env bash
cd $HOME/repos/weatherbot
set -o allexport
. .env
set +o allexport
$HOME/repos/weatherbot/.venv/bin/python main.py --post --email
