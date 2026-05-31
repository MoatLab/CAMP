#!/bin/bash
remote=$1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MLC_DIR="$(dirname "$SCRIPT_DIR")/mlc"

${MLC_DIR}/mlc --idle_latency -e -c0 -j$1 -x2000 -b1000000 -l256 > log 2> err
