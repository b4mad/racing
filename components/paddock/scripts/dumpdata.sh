#!/usr/bin/env sh

set -x
cd "$(dirname "$0")/.."

models="game car track sessiontype session driver coach fastlap fastlapsegment lap trackguide trackguidenote landmark"
# models="trackguide trackguidenote"
# models="fastlap fastlapsegment"
models=""
for o in $models; do
  pipenv run ./manage.py dumpdata --indent 2 telemetry.$o > telemetry/fixtures.all/$o.json
done

models="copilot copilotinstance profile"
models=""
for o in $models; do
  pipenv run ./manage.py dumpdata --indent 2 b4mad_racing_website.$o > b4mad_racing_website/fixtures.all/$o.json
done
