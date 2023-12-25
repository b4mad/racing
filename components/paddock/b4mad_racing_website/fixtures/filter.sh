#!/usr/bin/env sh
set -x
cd $(dirname $0)
jq '[.[] | select(.pk == 1 or .pk == 2 or .pk == 3)]' ../fixtures.all/copilot.json > copilot.json
jq '[.[] | select(.fields.driver == 7)]' ../fixtures.all/copilotinstance.json > copilotinstance.json
jq '[.[] | select(.pk == 7)]' ../fixtures.all/profile.json > profile.json
