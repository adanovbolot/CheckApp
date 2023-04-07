import os
from celery import Celery
from celery import shared_task

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main.settings')
app = Celery('main')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.task_routes = {
    'app.tasks.process_check': {'queue': 'check_processing'},
}


indicators_for_total = {
    'eng': ['total', 'total:', 'sum', 'aggregate', 'entire', 'overall', 'complete', 'comprehensive', 'gross',
            'absolute', 'final', 'whole'],
    'rus': ['итог', 'итог:', 'итого', 'итого:', 'оплате:', 'сумма:', 'сумма', 'всего', 'итоговая сумма',
            'общая сумма', 'общий итог', 'полная сумма', 'совокупная сумма', 'итоговая стоимость',
            'окончательная сумма', 'общая стоимость']
}


def parse_date(date_str):
    from datetime import datetime
    formats = ['%d.%m.%y', '%d.%m.%Y', '%m/%d/%Y', '%m/%d/%y', '%Y-%m-%d']
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            pass
    return None


@shared_task
def process_check(image_path, check_id):
    from django.utils import timezone
    from decimal import Decimal
    from rest_framework import serializers
    import re
    from PIL import ImageEnhance, Image
    import pytesseract
    from app.models import Check, Currency, PercentageCashbackCheck
    from django.utils.translation import gettext as _

    with Image.open(image_path) as img:
        img = img.convert('L')
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)
        languages = ['eng', 'rus']
        text = pytesseract.image_to_string(img, lang='+'.join(languages), config='--psm 6')
        text = text.lower().split('\n')
        check = Check.objects.get(id=check_id)
        for i, line in enumerate(text):
            for lang, indicators in indicators_for_total.items():
                for indicator in indicators:
                    if indicator in line:
                        total = None
                        match = re.search(r'[=]?\d+[.,]?\d*', text[i + 1])
                        if match:
                            total_str = match.group().replace(',', '.').lstrip('=')
                            total = float(total_str)
                            check.total = total
                            break
            date_regex = r'\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b'
            search_date = re.search(date_regex, line)
            if search_date:
                date_str = search_date.group()
                check_creation_date = parse_date(date_str)
                if check_creation_date:
                    check.check_creation_date = check_creation_date
        check.general_info = '\n'.join(text)
        if check.check_creation_date is None or check.total is None:
            check.status = 1
        else:
            if check.check_creation_date != timezone.now().date():
                check.status = 3
            else:
                check.status = 2
        check.save()
        if check.status == 2:
            user = check.user
            total = check.total
            currency = user.currency.char_code
            if currency == 'USD':
                converted_total = Decimal(total)
            else:
                try:
                    currency_obj = Currency.objects.get(char_code='USD', is_active=True)
                except Currency.DoesNotExist:
                    raise serializers.ValidationError(
                        {'Сообщение': _('Не удается найти активную валюту в долларах США.')})
                actual_value = Decimal(currency_obj.actual_value)
                if currency == 'RUB':
                    converted_total = Decimal(total) / actual_value
                elif currency == 'EUR':
                    converted_total = Decimal(total) * actual_value
                else:
                    raise serializers.ValidationError({'Сообщение': _('Недопустимая валюта.')})
            cashback_percentage = Decimal(PercentageCashbackCheck.objects.first().points)
            cashback_amount = converted_total * cashback_percentage / Decimal(100)
            if cashback_amount > user.price_limit:
                raise serializers.ValidationError({'Сообщение': _('Превышен лимит для кэшбэка')})
            user.balance += cashback_amount
            user.save()

        return "Задача выполнена успешно"
