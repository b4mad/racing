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

### updating models

```bash
Lap.objects.update(valid=False)
```

### replaying

```bash
# speed ratio, oschersleben, brake now -> brake
python manage.py replay --session-id 1677132130
```

### profiling

```bash
sudo austin -i 100 -o ../../.vscode/output.austin  ./manage.py pitcrew -c durandom --replay
```

## production server

is using asgi, see https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/uvicorn/

```bash
python -m gunicorn paddock.asgi:application -k uvicorn.workers.UvicornWorker
```
