#!/usr/bin/env sh
set -x
cd $(dirname $0)
jq '[.[] | select(.pk == 1 or .pk == 5)]' ../fixtures.all/game.json > game.json
# jq '[.[] | select(.fields.game == 1 or .fields.game == 5)]' ../fixtures.all/car.json > car.json
jq '[.[] | select(.fields.name == "Ferrari 488 GT3 Evo 2020")]' ../fixtures.all/car.json > car.json
jq '[.[] | select(.fields.name == "fuji nochicane")]' ../fixtures.all/track.json > track.json
jq '[.[] | select(.fields.car == 9 and .fields.track == 409 )]' ../fixtures.all/fastlap.json > fastlap.json
jq '[.[] | select(.fields.fast_lap == 157 )]' ../fixtures.all/fastlapsegment.json > fastlapsegment.json
jq '[.[] | select(.pk == 10 )]' ../fixtures.all/coach.json > coach.json
jq '[.[] | select(.pk == 10 )]' ../fixtures.all/driver.json > driver.json
