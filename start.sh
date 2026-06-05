#!/usr/bin/env bash
set -o errexit

export PYTHONPATH=src
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
