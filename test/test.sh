#!/bin/bash
cd "$(dirname "$0")"
g++ -g -fkeep-inline-functions a.cpp -o /tmp/a.out
gdb -q /tmp/a.out -ex run -ex 'python exec(open("test.py", "r", encoding="u8").read())' </dev/null
