#!/usr/bin/env bash

p=$(mktemp -d)

python3.10 -m venv $p/venv
source $p/venv/bin/activate
micropipenv install --dev

python manage.py migrate
# python manage.py load_devel_data

python manage.py test telemetry

## end.
