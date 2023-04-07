import random
from django.core.mail import send_mail
from .models import EmailActive
from django.utils.translation import gettext_lazy as _


def generate_confirmation_code(email):
    code = ''.join(random.choices('0123456789', k=4))
    EmailActive.objects.filter(email=email).delete()
    return code


def send_email(email, code):
    message = _(f'Ваш код активации: {code}')
    send_mail(_('Код активации'), message, 'from@example.com', [email], fail_silently=False)
