#!/usr/bin/env sh

set -x
cd "$(dirname "$0")"


mosquitto_sub -u crewchief -P crewchief \
  -t "crewchief/durandom/#" \
  -p 31883 -h telemetry.b4mad.racing -i test -d
