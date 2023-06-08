#!/usr/bin/env sh
set -x
cd $(dirname $0)
jq '[.[] | select(.pk == 1 or .pk == 5)]' ../fixtures.all/game.json > game.json
# jq '[.[] | select(.fields.game == 1 or .fields.game == 5)]' ../fixtures.all/car.json > car.json
jq '[.[] | select(.pk == 9 or .pk == 351)]' ../fixtures.all/car.json > car.json
jq '[.[] | select(.pk == 409 or .pk == 83 or .pk == 1040)]' ../fixtures.all/track.json > track.json
jq '[.[] | select(.pk == 10 )]' ../fixtures.all/coach.json > coach.json
jq '[.[] | select(.pk == 10 or .pk == 1)]' ../fixtures.all/driver.json > driver.json
jq '[.[] | select(.pk == 703 or .pk == 157 or .pk == 1237)]' ../fixtures.all/fastlap.json > fastlap.json
jq '[.[] | select(.fields.fast_lap == 703 or .fields.fast_lap == 157 or .fields.fast_lap == 1237)]' ../fixtures.all/fastlapsegment.json > fastlapsegment.json
jq '[.[] | select(.fields.fast_lap == 703 or .fields.fast_lap == 157 or .fields.fast_lap == 1237)]' ../fixtures.all/lap.json > lap.json
jq '[.[] | select(.pk == 24222 or .pk == 26684 or .pk == 57153)]' ../fixtures.all/session.json > session.json
cp ../fixtures.all/sessiontype.json sessiontype.json
