#!/usr/bin/env bash
# AR AI 1.5 - Local Model Server Launcher for OpenClaw
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "Starting AR AI 1.5 Local Inference Server on port 8088..."
export PYTHONUNBUFFERED=1
exec ./mlx_env/bin/python -u arai_server.py
