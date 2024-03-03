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

* https://catalog.redhat.com/software/containers/crunchydata/crunchy-postgres/595e65ef1fbe9833203ff782
* https://catalog.redhat.com/software/containers/crunchydata/crunchy-pgbackrest/6011d5992937381f8e956d7f

and look for `ubi8-14` images for postgres 14.
But removing the image spec from the postgrescluster CR will use the default image.

# Register the operator

Crunchy Postgres for Kubernetes now requires registration for operator upgrades. Register now to be ready for your next upgrade. See https://access.crunchydata.com/register-cpk for details.

## WTF uid changes after OCP cluster upgrade

```
2024-01-24 16:24:35,105 INFO: Lock owner: ; I am db-instance-hnkw-0
2024-01-24 16:24:35,105 INFO: starting as a secondary
2024-01-24 16:24:35,451 ERROR: Exception during execution of long running task restarting after failure
Traceback (most recent call last):
File "/usr/local/lib/python3.6/site-packages/patroni/async_executor.py", line 166, in run
wakeup = func(*args) if args else func()
File "/usr/local/lib/python3.6/site-packages/patroni/postgresql/__init__.py", line 1094, in follow
ret = self.start(timeout=timeout, block_callbacks=change_role, role=role) or None
File "/usr/local/lib/python3.6/site-packages/patroni/postgresql/__init__.py", line 701, in start
self.config.write_postgresql_conf(configuration)
File "/usr/local/lib/python3.6/site-packages/patroni/postgresql/config.py", line 465, in write_postgresql_conf
self._sanitize_auto_conf()
File "/usr/lib64/python3.6/contextlib.py", line 88, in __exit__
next(self.gen)
File "/usr/local/lib/python3.6/site-packages/patroni/postgresql/config.py", line 394, in config_writer
self.set_file_permissions(filename)
File "/usr/local/lib/python3.6/site-packages/patroni/postgresql/config.py", line 382, in set_file_permissions
os.chmod(filename, pg_perm.file_create_mode)
PermissionError: [Errno 1] Operation not permitted: '/pgdata/pg14/postgresql.conf'
/tmp/postgres:5432 - no response
2024-01-24 16:24:35,479 ERROR: unable to create backup copies of configuration files
Traceback (most recent call last):
File "/usr/local/lib/python3.6/site-packages/patroni/postgresql/config.py", line 408, in save_configuration_files
shutil.copy(config_file, backup_file)
```

The uid of the postgres user changed from 1000750000 to 1000800000

```
❯ oc logs sts/db-instance-hnkw -f -c postgres-startup
Initializing ...
::postgres-operator: uid::1000800000
::postgres-operator: gid::0 1000800000
::postgres-operator: postgres path::/usr/pgsql-14/bin/postgres
::postgres-operator: postgres version::postgres (PostgreSQL) 14.10
::postgres-operator: config directory::/pgdata/pg14
::postgres-operator: data directory::/pgdata/pg14
::postgres-operator: pgBackRest log directory::/pgdata/pgbackrest/log
::postgres-operator: data version::14
::postgres-operator: wal directory::/pgdata/pg14_wal

❯ oc rsh sts/db-instance-hnkw
sh-4.4$ ls -la /pgdata/
total 24
drwxrwsrwx.  5 root       postgres    52 Aug 22 17:08 .
dr-xr-xr-x.  1 root       root        56 Jan 24 17:46 ..
drwx--S---. 19 postgres   postgres  4096 Jan 24 16:23 pg14
drwxrws---.  3 1000750000 postgres 65536 Jan 24 15:35 pg14_wal
drwxrwsr-x.  3 1000750000 postgres    17 May  3  2023 pgbackrest
```

We can't change the uid of the postgres user in the container, so we need to change the uid of the files in the volume.

```
❯ oc get pvc db-instance-hnkw-pgdata -o yaml | grep volumeName
  volumeName: pvc-d290bea6-77ab-4b22-95b0-608b814ed036

oc debug node/phobos
sh-4.4# mount | grep pvc-d290bea6-77ab-4b22-95b0-608b814ed036
/dev/topolvm/6c4c5f6a-f0f5-4342-98c8-9179e01671ca on /host/var/lib/kubelet/pods/bee3afd8-80d0-4dff-be1c-8134aaa9d11b/volumes/kubernetes.io~csi/pvc-d290bea6-77ab-4b22-95b0-608b814ed036/mount type xfs (rw,relatime,seclabel,nouuid,attr2,inode64,logbufs=8,logbsize=128k,sunit=256,swidth=256,noquota)
sh-4.4# cd /host/var/lib/kubelet/pods/bee3afd8-80d0-4dff-be1c-8134aaa9d11b/volumes/kubernetes.io~csi/pvc-d290bea6-77ab-4b22-95b0-608b814ed036/
sh-4.4# ls -la
total 4
drwxr-x---. 3 root root        40 Jan 24 20:04 .
drwxr-x---. 3 root root        54 Jan 24 20:04 ..
drwxrwsrwx. 5 root 1000800000  52 Aug 22 17:08 mount
-rw-r--r--. 1 root root       278 Jan 24 20:04 vol_data.json
find mount -uid 1000750000 -exec chown -h 1000800000 {} \;
```
