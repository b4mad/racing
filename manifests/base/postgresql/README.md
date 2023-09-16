<https://github.com/CrunchyData/postgres-operator-examples/blob/main/kustomize/postgres/postgres.yaml>

<https://access.crunchydata.com/documentation/postgres-operator/latest/tutorials/backups-disaster-recovery/backup-management>
oc annotate postgrescluster db postgres-operator.crunchydata.com/pgbackrest-backup="$(date)"
oc annotate postgrescluster db --overwrite postgres-operator.crunchydata.com/pgbackrest-backup="$(date)"

# Run from cronjob

oc create job --from=cronjob/db-repo1-diff db-repo1-diff

### Run a pgbackrest one off inside the db pod

```
oc rsh sts/db-instance-hnkw
pgbackrest backup --stanza=db --repo=1 --type=full
```

# Upgrade to psql 15

<https://forum.djangoproject.com/t/a-guide-to-setting-up-django-with-postgresql-15/16514/4>
<https://gist.github.com/axelbdt/74898d80ceee51b69a16b575345e8457>

# What container images are available
<https://www.crunchydata.com/developers/download-postgres/containers/postgresql14>
<https://catalog.redhat.com/software/containers/crunchydata/crunchy-pgbackrest/6011d5992937381f8e956d7f>
