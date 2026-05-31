#!/bin/bash
remote=$1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MLC_DIR="$(dirname "$SCRIPT_DIR")/mlc"

${MLC_DIR}/mlc --idle_latency -e -c0 -j$1 -x500 -b2000000 -r > log 2> err
