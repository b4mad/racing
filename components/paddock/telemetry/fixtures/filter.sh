#!/usr/bin/env sh
set -x
cd $(dirname $0)
jq '[.[] | select(.pk == 1 or .pk == 5)]' ../fixtures.all/game.json > game.json
# jq '[.[] | select(.fields.game == 1 or .fields.game == 5)]' ../fixtures.all/car.json > car.json
jq '[.[] | select(.pk == 9 or .pk == 351)]' ../fixtures.all/car.json > car.json
jq '[.[] | select(.pk == 409 or .pk == 83)]' ../fixtures.all/track.json > track.json
jq '[.[] | select(.fields.car == 9 and .fields.track == 409 )]' ../fixtures.all/fastlap.json > fastlap.json
jq '[.[] | select(.fields.fast_lap == 157 )]' ../fixtures.all/fastlapsegment.json > fastlapsegment.json
jq '[.[] | select(.pk == 10 )]' ../fixtures.all/coach.json > coach.json
jq '[.[] | select(.pk == 10 or .pk == 1)]' ../fixtures.all/driver.json > driver.json
jq '[.[] | select(.pk == 37672 or .pk == 40781)]' ../fixtures.all/lap.json > lap.json
jq '[.[] | select(.pk == 24222 or .pk == 26684)]' ../fixtures.all/session.json > session.json
cp ../fixtures.all/sessiontype.json sessiontype.json
