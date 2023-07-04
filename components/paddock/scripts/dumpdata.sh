#!/usr/bin/env sh

set -x
cd "$(dirname "$0")/.."

models="game car track sessiontype session driver coach fastlap fastlapsegment lap"
models="fastlapsegment lap"
for o in $models; do
  pipenv run ./manage.py dumpdata --indent 2 telemetry.$o > telemetry/fixtures.all/$o.json
done
