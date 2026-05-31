#!/bin/bash
node=$1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BW_DIR="$(dirname "$SCRIPT_DIR")/bw"

$BW_DIR/bw -t 1 -s 1024 -i 100 -n $node -m r
