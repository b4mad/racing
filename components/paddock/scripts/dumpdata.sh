#!/usr/bin/env sh

set -x
cd "$(dirname "$0")/.."

models="game car track sessiontype session driver coach fastlap fastlapsegment lap trackguide trackguidenote landmark"
models="trackguide trackguidenote"
for o in $models; do
  pipenv run ./manage.py dumpdata --indent 2 telemetry.$o > telemetry/fixtures.all/$o.json
done
