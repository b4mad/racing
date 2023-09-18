#!/usr/bin/env bash

shopt -s extglob
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd $script_dir

# assuming we are running on a containerized venv...
pip install micropipenv

# prepare another venv with paddock's dependencies
p=$(mktemp -d)
python3.10 -m venv $p/venv
source $p/venv/bin/activate
micropipenv install --dev
cd ..

# run the actual pytests
pytest -v

## end.
