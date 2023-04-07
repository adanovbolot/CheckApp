#!/bin/bash
python manage.py makemigrations
python manage.py migrate
service cron start
python manage.py crontab add
python manage.py crontab show
gunicorn main.wsgi:application --bind 0.0.0.0:8000
