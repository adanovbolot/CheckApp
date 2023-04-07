from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from phonenumber_field.modelfields import PhoneNumberField
from django.utils.translation import gettext_lazy as _
from random import randint
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from main import settings
from decimal import Decimal


class MyUserManager(BaseUserManager):
    def create_user(self, date_of_birth=None, username=None,
                    email=None, password=None, phone_number=None,
                    city=None, country=None, currency=None):
        user = self.model(
            city=city,
            country=country,
            date_of_birth=date_of_birth,
            username=username,
            email=email,
            phone_number=phone_number,
            currency=currency
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, date_of_birth, username=None, email=None, password=None, phone_number=None):
        user = self.create_user(
            date_of_birth=date_of_birth,
            username=username,
            email=email,
            password=password,
            country=None,
            phone_number=phone_number,
            city=None,
        )
        user.is_admin = True
        user.is_active = True
        user.is_verified = True
        user.save(using=self._db)
        return user


class CardNumber(models.Model):
    user = models.ForeignKey(
        'MyUser',
        on_delete=models.SET_NULL,
        verbose_name=_('Пользователь'),
        related_name='rel_user',
        null=True
    )
    card_number = models.CharField(
        verbose_name=_('Номер карты'),
        max_length=19,
        unique=True
    )
    created_date = models.DateTimeField(
        verbose_name=_('Дата создания'),
        auto_now_add=True
    )
    is_active = models.BooleanField(
        verbose_name=_('Активен'),
        default=True
    )
    withdrawal_card = models.BooleanField(
        default=False,
        verbose_name=_('Карта для вывода')
    )

    def __str__(self):
        return f"{self.user}, {self.card_number}"

    class Meta:
        verbose_name = _('Банковская карта')
        verbose_name_plural = _('Банковские карта')

    def set_withdrawal_card(self):
        self.user.rel_user.exclude(id=self.id).update(withdrawal_card=False)
        self.withdrawal_card = True
        self.save()

    def save(self, *args, **kwargs):
        if self.withdrawal_card:
            CardNumber.objects.filter(user=self.user, withdrawal_card=True).exclude(id=self.id).update(
                withdrawal_card=False)
        super().save(*args, **kwargs)


class MyUser(AbstractBaseUser):
    email = models.EmailField(
        verbose_name=_('Email'),
        max_length=255,
        null=True,
        blank=True,
        unique=True
    )
    username = models.CharField(
        verbose_name=_('Имя'),
        max_length=50,
        null=True,
        blank=True
    )
    phone_number = PhoneNumberField(
        verbose_name=_('Номер'),
        null=True,
        blank=True,
        unique=True
    )
    date_of_birth = models.DateField(
        verbose_name=_('Дата рождения'),
        null=True,
        blank=True
    )
    image = models.ImageField(
        upload_to='media/images',
        default='media/images/msg1763925874-35448.jpg',
        verbose_name=_('Фотография профиля'),
        null=True,
        blank=True
    )
    country = models.ForeignKey(
        'Country',
        on_delete=models.PROTECT,
        verbose_name=_('Страна'),
        null=True,
        blank=True
    )
    city = models.ForeignKey(
        'City',
        verbose_name=_('Город'),
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    agreement = models.ForeignKey(
        'Agreement',
        on_delete=models.PROTECT,
        verbose_name=_('Пользовательское соглашение'),
        null=True,
        blank=True,
    )
    currency = models.ForeignKey(
        'app.Currency',
        on_delete=models.SET_NULL,
        verbose_name=_('Валюта'),
        blank=True,
        null=True
    )
    balance = models.DecimalField(
        verbose_name=_('Баланс'),
        decimal_places=2,
        max_digits=12,
        default=0.00
    )
    level = models.PositiveSmallIntegerField(
        verbose_name=_('Уровень'),
        default=1
    )
    today_amount = models.DecimalField(
        decimal_places=2,
        max_digits=12,
        verbose_name=_('Сегодняшняя сумма'),
        default=0
    )
    price_limit = models.DecimalField(
        verbose_name=_('Ежедневный лимит'),
        decimal_places=2,
        max_digits=12,
        null=True,
        blank=True
    )
    featured_actions = models.ManyToManyField(
        'app.FeaturedUserAction',
        related_name='users',
        blank=True,
        verbose_name=_('Избранные'),
    )
    buying_action = models.ManyToManyField(
        'app.BuyingAction',
        blank=True,
        verbose_name=_('Купленные акции')
    )
    invitation_code = models.CharField(
        verbose_name=_('Пригласительный код'),
        default=randint(100000, 999999),
        max_length=7
    )
    card_number = models.ForeignKey(
        CardNumber,
        verbose_name=_('Номер карты'),
        related_name='rel_card',
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )
    is_active = models.BooleanField(
        verbose_name=_('Активен'),
        default=True
    )
    is_admin = models.BooleanField(
        verbose_name=_('Админ'),
        default=False
    )
    is_verified = models.BooleanField(
        verbose_name=_('Проверено'),
        default=False
    )
    language = models.CharField(
        max_length=10,
        choices=settings.LANGUAGES,
        default=settings.LANGUAGE_CODE,
        verbose_name=_("Язык"),
    )
    date_of_registration = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Дата регистрации'),
        null=True,
        blank=True
    )
    last_reset_time = models.DateTimeField(
        verbose_name=_('Время последнего обнуления'),
        null=True,
        blank=True
    )

    objects = MyUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['date_of_birth']

    class Meta:
        verbose_name = _('Пользователь')
        verbose_name_plural = _('Пользователи')
        indexes = [
            models.Index(fields=['date_of_registration'])
        ]
        unique_together = ('email', 'phone_number', 'date_of_birth')

    def get_active_currency(self):
        if self.currency and self.currency.is_active:
            return self.currency
        return None

    def delete(self, using=None, keep_parents=False):
        self.is_active = False
        self.date_of_registration = timezone.now()
        self.date_of_registration = None
        self.save()

    def create(self, validated_data):
        from app.models import LevelPayment
        level = LevelPayment.objects.create(
            user=validated_data['user'],
            level=validated_data['level']
        )
        validated_data['user'].level = validated_data['level'].level
        validated_data['user'].save()
        return level

    def reset_today_amount(self):
        self.today_amount = self.balance
        self.save()

    @staticmethod
    def get_default_level_price():
        from app.models import LevelPrice
        level_price = LevelPrice.objects.filter(level=1).first()
        return level_price

    def save(self, *args, **kwargs):
        if not self.pk:
            self.level_price = self.get_default_level_price()
            if self.level_price:
                self.price_limit = self.level_price.limit
            self.today_amount = self.balance
        else:
            last_reset_time = self.last_reset_time or timezone.now() - timezone.timedelta(days=1)
            if (timezone.now() - last_reset_time) >= timezone.timedelta(hours=24):
                self.today_amount = self.balance
                self.last_reset_time = timezone.now()
            if self.balance != self.today_amount:
                self.today_amount = self.balance
        if self.today_amount is not None and self.price_limit is not None:
            if self.today_amount > self.price_limit:
                raise ValueError(_('Сегодняшняя сумма не может превышать лимит'))
        super().save(*args, **kwargs)

        if self.today_amount is not None and self.price_limit is not None:
            if self.today_amount > self.price_limit:
                raise ValueError(_('Сегодняшняя сумма не может превышать лимит'))
        super().save(*args, **kwargs)

    def __str__(self):
        if self.username:
            return f'{self.username} Уровень {self.level}'
        elif self.email:
            return f'{self.email} Уровень {self.level}'
        elif self.phone_number:
            return f'{self.phone_number} Уровень {self.level}'
        else:
            return f'{self.id}, Уровень {self.level}, Страна {self.country}'

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

    @property
    def is_staff(self):
        return self.is_admin


class Cashback(models.Model):
    cashback = models.DecimalField(
        verbose_name=_('Кэшбэк'),
        decimal_places=2,
        max_digits=12
    )

    class Meta:
        verbose_name = _('Кэшбэк')
        verbose_name_plural = _('Кэшбэк')

    def __str__(self):
        return f"{self.cashback}"

    def clean(self):
        num_cashback = Cashback.objects.count()
        if num_cashback > 1:
            raise ValidationError(_('Можно создать только один объект Cashback'))


class EmailActive(models.Model):
    user = models.OneToOneField(
        MyUser,
        verbose_name=_('Пользователь'),
        related_name='email_active',
        on_delete=models.CASCADE,
    )
    email = models.EmailField(
        verbose_name=_('Email')
    )
    code = models.CharField(
        max_length=4,
        verbose_name=_('Код')
    )
    is_active = models.BooleanField(
        default=False,
        verbose_name=_('Email активирован')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата активации email')
    )

    def __str__(self):
        return f"{self.email} - {self.code}"

    def check_code(self, code):
        return self.code == code


class Agreement(models.Model):
    agree_disagree = models.BooleanField(
        default=False,
        verbose_name=_('Пользователькая соглашения')
    )
    title = models.CharField(
        max_length=100,
        verbose_name=_('Заглавие соглашения')
    )
    description = models.TextField(
        verbose_name=_('Описание соглашения')
    )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = _('Пользовательское соглашение')
        verbose_name_plural = _('Пользовательские соглашения')


class Country(models.Model):
    name = models.CharField(
        verbose_name=_('Название страны'),
        max_length=123
    )
    char_code = models.CharField(
        max_length=10,
        verbose_name=_('Домены стран'),
    )
    phone_code = models.CharField(
        max_length=50,
        verbose_name=_('Код телефона')
    )
    flag = models.ImageField(
        upload_to='media/flags',
        verbose_name=_('Флаг'),
        max_length=255
    )

    def save(self, *args, **kwargs):
        self.char_code = self.char_code.upper()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Страна')
        verbose_name_plural = _('Страны')


class City(models.Model):
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        verbose_name=_('Страна'),
        related_name='city_data'
    )
    name = models.CharField(
        verbose_name=_('Название города'),
        max_length=123
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Город')
        verbose_name_plural = _('Города')
