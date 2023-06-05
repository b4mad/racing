# The #B4mad Racing Paddock

## development

### setup

To setup the development environment, you need to create a new virtual environment for the python dependencies, and install them

```bash
python3.10 -m venv venv
source venv/bin/activate
micropipenv install --dev
```

Followed by the database setup

```bash
python manage.py migrate
```

If you want to load some test data into the database, you can use the following command:

```bash
python manage.py load_devel_data
```

### run

To run the application, you can use the following command:

```bash
python manage.py runserver
```

### admin

```shell
pipenv run ./manage.py createsuperuser
```

### updating models

```shell
Lap.objects.update(valid=False)
```

### tests

```shell
python manage.py test telemetry
```

### replaying

```shell
# speed ratio, oschersleben, brake now -> brake
pipenv run ./manage.py replay --session-id 1677132130
```

#### replaying a session with a coach

```shell
pipenv run ./manage.py pitcrew -c durandom --replay
pipenv run ./manage.py replay --session-id 1683915879 --change-driver durandom --wait 0.01
```

### profiling

```shell
pipenv shell
sudo austin -i 100 -o ../../.vscode/output.austin  ./manage.py pitcrew -c durandom --replay
in vscode open the output.austin file
https://marketplace.visualstudio.com/items?itemName=p403n1x87.austin-vscode
shift-cmd-p view flamegraph
```

### notebooks

<https://blog.theodo.com/2020/11/django-jupyter-vscode-setup/>

```shell
pipenv run ./manage.py shell_plus --notebook
```

### scratch

* check all valid laps for consistency
  * same length as track
  * end - start == lap time
