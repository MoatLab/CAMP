#!/bin/bash
node=$1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BW_DIR="$(dirname "$SCRIPT_DIR")/bw"

$BW_DIR/bw -t 2 -s 8192 -i 1 -n $node -m r
