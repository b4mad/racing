#!/usr/bin/env bash
set -x

# exit on failure
# set -e

oc project b4mad-racing

oc rollout restart deployment telegraf
oc rollout restart deployment grafana-deployment
oc rollout latest dc/paddock
