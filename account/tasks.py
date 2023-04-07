from datetime import datetime, timedelta
from celery import shared_task
from django.contrib.auth import get_user_model

User = get_user_model()


@shared_task
def delete_user():
    users_to_delete = User.objects.filter(date_created__lte=datetime.now() - timedelta(days=30))
    users_to_delete.delete()
