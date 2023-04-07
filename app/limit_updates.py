import os
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings')

import django
from django.conf import settings

if not settings.configured:
    django.setup()

from account.models import MyUser
from app.models import Action


def limit_updates_function():
    users = MyUser.objects.filter(is_active=True, is_verified=True).update(today_amount=0)
    print(users)

limit_updates_function()


def action_limit():
    actions = Action.objects.filter(end_date__lt=datetime.today().date()).update(is_active=False)
    print(actions)


action_limit()


