#!/usr/bin/env bash

PG_CLUSTER_PRIMARY_POD=$(kubectl get pod -n b4mad-racing -o name -l postgres-operator.crunchydata.com/cluster=b4mad-racing,postgres-operator.crunchydata.com/role=master)
echo $PG_CLUSTER_PRIMARY_POD

kubectl -n b4mad-racing port-forward "${PG_CLUSTER_PRIMARY_POD}" 5432:5432
