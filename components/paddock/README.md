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
