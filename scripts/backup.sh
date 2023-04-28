#!/usr/bin/env sh

set -x
cd "$(dirname "$0")/.."

scripts/pg_dump.sh

DATE=$(date +%Y-%m-%d_%H-%M-%S)
influx backup --bucket racing data/influx_racing-${DATE}
influx backup --bucket fast_laps data/influx_fast_laps-${DATE}
