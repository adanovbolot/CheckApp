import os
import requests
from datetime import datetime, timedelta
from decimal import Decimal
from xml.etree import ElementTree
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings')

import django
from django.conf import settings

if not settings.configured:
    django.setup()

from app.models import Currency


def get_actual_currency():
    Currency.objects.filter(created_date__lt=timezone.now() - timedelta(hours=24)).update(is_active=False)
    url = "http://www.cbr.ru/scripts/XML_daily.asp"
    payload = {}
    headers = {}
    response = requests.request("GET", url, headers=headers, data=payload)
    if response.status_code != 200:
        return
    root = ElementTree.fromstring(response.content)
    currencies = {}
    for valute in root.findall('Valute'):
        char_code = valute.find('CharCode').text
        nominal = Decimal(valute.find('Nominal').text.replace(',', '.'))
        value = Decimal(
            valute.find('Value').text.replace(',', '.').replace(' ', '')) / nominal
        currencies[char_code] = value
    usd_value = currencies.get('USD')
    if usd_value is not None:
        Currency.objects.update_or_create(
            char_code='USD',
            defaults={'actual_value': Decimal(1), 'is_active': True}
        )
    eur_value = currencies.get('EUR')
    if 'USD' in currencies and eur_value is not None:
        eur_value = eur_value / usd_value
        Currency.objects.update_or_create(
            char_code='EUR',
            defaults={'actual_value': eur_value.quantize(Decimal('.01')), 'is_active': True}
        )
        rub_value = Decimal(1) * usd_value
        Currency.objects.update_or_create(
            char_code='RUB',
            defaults={'actual_value': rub_value.quantize(Decimal('.01')), 'is_active': True}
        )

# RUB	81,60	6 April 2023 г. 19:41	True
# EUR	1,09	6 April 2023 г. 19:41	True
# USD	1,00	6 April 2023 г. 19:41	True

get_actual_currency()
