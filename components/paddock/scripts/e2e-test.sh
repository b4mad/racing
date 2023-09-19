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

# set up the django app and its database
python manage.py migrate
# python manage.py load_devel_data

# run the actual telemetry tests
python manage.py test telemetry

## end.
