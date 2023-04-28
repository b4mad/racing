#!/usr/bin/env sh

set -x
cd "$(dirname "$0")/.."

DATE=$(date +%Y-%m-%d_%H-%M-%S)

./manage.py maintenance --delete-sessions
# ./manage.py replay --firehose --live --keep-session-id --end 'now()' --start=2022-12-30 --wait=0 --quiet --bucket=fast_laps --measurement=fast_laps --delta=1d
./manage.py replay --firehose --live --keep-session-id --end 'now()' --start=2023-04-01 --wait=0 --quiet --bucket=fast_laps --measurement=fast_laps --delta=1d
./manage.py replay --firehose --live --keep-session-id --end 'now()' --start=-32d --wait=0 --quiet --delta=1h



# SESSIONS=(1680319016
# 1680321341
# 1680320700
# 1680301061
# 1680321317)

# for SESSION in "${SESSIONS[@]}"; do
#   echo "replaying session $SESSION"
#   pipenv run ./manage.py replay --live --session-id $SESSION --firehose --bucket=fast_laps --measurement=fast_laps --wait=0
# done
