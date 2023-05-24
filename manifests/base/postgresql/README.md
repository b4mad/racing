https://github.com/CrunchyData/postgres-operator-examples/blob/main/kustomize/postgres/postgres.yaml


https://access.crunchydata.com/documentation/postgres-operator/v5/tutorial/backup-management/
oc annotate postgrescluster db postgres-operator.crunchydata.com/pgbackrest-backup="$(date)"
oc annotate postgrescluster db --overwrite postgres-operator.crunchydata.com/pgbackrest-backup="$(date)"
