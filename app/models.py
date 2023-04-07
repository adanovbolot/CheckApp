from PIL import Image
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.core.exceptions import ValidationError
from datetime import datetime
from decimal import Decimal
from account.models import Country, MyUser
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


User = get_user_model()


class CategoriesSupport(models.Model):
    class Meta:
        verbose_name = _('Категория техподдержка')
        verbose_name_plural = _('Категории техподдержка')

    title_category = models.CharField(
        verbose_name=_('Тема вопроса'),
        max_length=200
    )

    def __str__(self):
        return f"{self.title_category}"


class QuestionAnswer(models.Model):
    question = models.CharField(
        max_length=255,
        verbose_name=_('Вопрос')
    )
    answer = models.TextField(
        verbose_name=_('Ответ')
    )

    def __str__(self):
        return self.question

    class Meta:
        verbose_name = _('Вопрос ответ')
        verbose_name_plural = _('Вопрос ответ')


class StockCategory(models.Model):
    section = models.CharField(
        max_length=123,
        verbose_name=_('Названия раздела')
    )

    def __str__(self):
        return self.section

    class Meta:
        verbose_name = _('Категория акций')
        verbose_name_plural = _('Категории акций')


class Action(models.Model):
    STATUS_CHOICES = (
        (1, _('Акции')),
        (2, _('Cпецпредложения')),
    )
    title = models.CharField(
        verbose_name=_('Заголовок'),
        max_length=125
    )
    description = models.TextField(
        verbose_name=_('Промо текст')
    )
    image = models.ImageField(
        upload_to='media/images/actions',
        verbose_name=_('Картинка')
    )
    cover_text = models.TextField(
        verbose_name=_('Сопроводительный текст')
    )
    start_date = models.DateField(
        verbose_name=_('Старт акции')
    )
    end_date = models.DateField(
        verbose_name=_('Конец акции')
    )
    price = models.DecimalField(
        verbose_name=_('Цена акции'),
        decimal_places=2,
        max_digits=12,
        blank=True,
        null=True
    )
    promo_code = models.CharField(
        max_length=50,
        verbose_name=_('Промокод'),
        blank=True,
        null=True
    )
    coupon = models.FileField(
        upload_to='media/images/coupon',
        verbose_name=_('Купон'),
        blank=True,
        null=True
    )
    section = models.ForeignKey(
        StockCategory,
        on_delete=models.CASCADE,
        verbose_name=_('Раздел'),
        related_name='actions'
    )
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        verbose_name=_('Страна'),
        null=True,
        blank=True
    )
    is_paid = models.BooleanField(
        verbose_name=_('Акция платная'),
        default=False
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Акция актуально')
    )
    status = models.PositiveSmallIntegerField(
        choices=STATUS_CHOICES,
        verbose_name=_('Статус'),
        blank=True,
        null=True
    )

    def clean(self):
        if self.promo_code and self.coupon:
            raise ValidationError(_('Нельзя указывать и промокод и купон одновременно'))

    def save(self, *args, **kwargs):
        super(Action, self).save(*args, **kwargs)
        if self.coupon:
            img = Image.open(self.image.path)
            if img.height > 370 or img.width > 716:
                output_size = (370, 716)
                img.thumbnail(output_size)
                img.save(self.image.path, quality=100)

        if self.coupon:
            img = Image.open(self.coupon.path)
            if img.height > 370 or img.width > 716:
                output_size = (370, 716)
                img.thumbnail(output_size)
                img.save(self.coupon.path, quality=100)
        if self.price is not None and isinstance(self.price, Decimal):
            self.is_paid = True

    class Meta:
        verbose_name = _('Акция')
        verbose_name_plural = _('Акции')

    def __str__(self):
        return self.title


@receiver(post_save, sender=Action)
def set_action_inactive(sender, instance, **kwargs):
    if instance.end_date < timezone.now().date():
        instance.is_active = False
        instance.save()


class FeaturedUserAction(models.Model):
    user = models.ForeignKey(
        MyUser,
        on_delete=models.CASCADE,
        verbose_name=_('Пользователь'),
        related_name='user_data'
    )
    action = models.ForeignKey(
        Action,
        on_delete=models.CASCADE,
        verbose_name=_('Акция'),
        related_name='action_company'

    )
    created_date = models.DateTimeField(
        verbose_name=_('Дата создания'),
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.user}"

    class Meta:
        verbose_name = _('Избранное')
        verbose_name_plural = _('Избранные')


class Currency(models.Model):
    char_code = models.CharField(
        max_length=10,
    )
    actual_value = models.DecimalField(
        verbose_name=_('Актуальная цена'),
        decimal_places=2,
        max_digits=12
    )
    created_date = models.DateTimeField(
        verbose_name=_('Дата создания'),
        auto_now_add=True
    )
    updated_date = models.DateTimeField(
        verbose_name=_('Дата изменения'),
        auto_now=True
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Курс актуален')
    )
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        verbose_name=_('Страна'),
        related_name='currencies',
        default=1,
        null=True
    )

    class Meta:
        verbose_name = _('Валюта')
        verbose_name_plural = _('Валюты')

    def __str__(self):
        return self.char_code


class PercentageCashbackCheck(models.Model):
    points = models.DecimalField(
        verbose_name=_('Баллы'),
        decimal_places=2,
        max_digits=12
    )

    def __str__(self):
        return f"{self.points}"

    class Meta:
        verbose_name = _('Процент кэшбэка с чека')
        verbose_name_plural = _('Процент кэшбэка с чеков')


class Company(models.Model):
    name = models.CharField(
        verbose_name=_('Название компании'),
        max_length=125
    )
    has_action = models.BooleanField(
        default=False,
        verbose_name=_('Имеются ли акции у данной компании')
    )
    action = models.ForeignKey(
        Action,
        on_delete=models.CASCADE,
        related_name='companies',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = _('Компания')
        verbose_name_plural = _('Компании')

    def save(self, *args, **kwargs):
        if self.action:
            self.has_action = True
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class CheckImage(models.Model):
    user = models.ForeignKey(
        MyUser,
        on_delete=models.CASCADE,
        verbose_name=_('Пользователь',)
    )


class Check(models.Model):
    STATUS_CHOICES = (
        (1, _('На проверке')),
        (2, _('Выполнен')),
        (3, _('Отклонен')),
    )
    user = models.ForeignKey(
        MyUser,
        on_delete=models.CASCADE,
        verbose_name=_('Пользователь'),
        related_name='checks'
    )
    image = models.ImageField(
        upload_to='media/images/checks',
        verbose_name=_('Чек'),
        max_length=255,
    )
    created_date = models.DateTimeField(
        verbose_name=_('Дата создания'),
        auto_now_add=True
    )
    total = models.DecimalField(
        verbose_name=_('Сумма'),
        decimal_places=2,
        max_digits=12,
        default=0
    )
    check_creation_date = models.DateField(
        verbose_name=_('Дата создания чека'),
        blank=True,
        null=True
    )
    general_info = models.TextField(
        verbose_name=_('Общая информация'),
        blank=True,
        null=True,
        unique=True
    )
    status = models.PositiveSmallIntegerField(
        choices=STATUS_CHOICES,
        default=1,
        verbose_name=_('Статус')
    )

    class Meta:
        verbose_name = _('Чек сделанный сканером')
        verbose_name_plural = _('Чеки сделанные сканером')
        ordering = ['-created_date']

    def cover_image(self):
        return format_html(f'<img src="{self.image.url}" style="width:100px;height:150px;" />')

    def str(self):
        return str(self.user)


class Slide(models.Model):
    file = models.FileField(_('Файлы'))
    ordering = models.SmallIntegerField(
        verbose_name=_('Позиция')
    )

    def cover_image(self):
        return format_html(f'<img src="{self.file.url}" style="width:100px;height:150px;" />')

    def __str__(self):
        return f"Идентификатор файла {self.id}"

    class Meta:
        verbose_name = _('Слайд')
        verbose_name_plural = _('Слайды')


class Passcode(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('Пользователь')
    )
    code = models.CharField(
        verbose_name=_('Код'),
        max_length=8,
        blank=True,
        null=True)
    created_date = models.DateTimeField(
        verbose_name=_('Дата создания'),
        auto_now_add=True
    )

    def __str__(self):
        return str(self.user)


class AnswerQuestion(models.Model):
    question = models.TextField(
        verbose_name=_('Вопрос')
    )
    categories_support = models.ForeignKey(
        CategoriesSupport,
        verbose_name=_('Категория вопроса'),
        on_delete=models.PROTECT
    )
    created_date = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Дата создания')
    )

    class Meta:
        verbose_name = _('Ответ на вопрос')
        verbose_name_plural = _('Ответы на вопросы')

    def __str__(self):
        return str(self.answer)


class Support(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('Пользователь')
    )
    answer_question = models.ForeignKey(
        AnswerQuestion,
        on_delete=models.CASCADE,
        verbose_name=_('Вопрос'),
        related_name='support'
    )
    category_support = models.ForeignKey(
        CategoriesSupport,
        on_delete=models.PROTECT,
        verbose_name=_('Техподдержка'),
        related_name='category'
    )
    description = models.TextField(
        verbose_name=_('Описание')
    )
    created_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Дата создания')
    )
    status = models.PositiveSmallIntegerField(
        choices=(
            (1, _('В обработке')),
            (2, _('Решено')),
        ),
        verbose_name=_('Статус'),
        default=1
    )

    class Meta:
        verbose_name = _('Техподдержка')
        verbose_name_plural = _('Техподдержка')

    def __str__(self):
        return f'{self.user} | {self.created_date}'


class LevelPrice(models.Model):
    level = models.PositiveSmallIntegerField(
        verbose_name=_('Уровень')
    )
    title = models.CharField(
        max_length=123,
        verbose_name=_('Название уровня'),
        null=True,
        blank=True
    )
    price = models.DecimalField(
        verbose_name=_('Цена уровня'),
        decimal_places=2,
        max_digits=12
    )
    limit = models.DecimalField(
        decimal_places=2,
        max_digits=12,
        verbose_name=_('Лимит в день')
    )
    created_date = models.DateField(
        auto_now=True,
        verbose_name=_('Дата создания')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Актуально?')
    )

    def __str__(self):
        return f'Уровень {self.level} Цена {self.price}'

    class Meta:
        verbose_name = _('Цена уровня')
        verbose_name_plural = _('Цены уровней')


class LevelPayment(models.Model):
    user = models.ForeignKey(
        MyUser,
        on_delete=models.CASCADE,
        verbose_name=_('Пользователь'),
        related_name='level_payments'
    )
    level = models.ForeignKey(
        LevelPrice,
        on_delete=models.CASCADE,
        verbose_name=_('Какой уровень'),
        related_name='level_payments'
    )
    created_date = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Дата создания')
    )
    status = models.PositiveSmallIntegerField(
        choices=(
            (1, _('На проверке')),
            (2, _('Выполнен')),
            (3, _('Отклонен')),
        ),
        default=2,
        verbose_name=_('Статус')
    )

    def clean(self):
        user = self.user
        level = self.level
        if user.level >= level.level:
            raise ValidationError(_('Ваш уровень больше или равен уровню, который вы хотите купить'))
        elif user.level != level.level - 1:
            raise ValidationError(_('Вы не можете перепрыгнуть через уровень'))
        elif self.status == 2:
            level_price = self.level.price
            if user.balance >= level_price:
                user.balance -= level_price
                user.level += 1
                user.price_limit = level.limit
                user.save()
                self.price = level_price
                return self
            raise ValidationError(_('У вас недостаточно средств'))
        return super().clean()

    def __str__(self):
        return str(self.user)

    class Meta:
        verbose_name = _('Оплата за уровень')
        verbose_name_plural = _('Оплата за уровни')


class ReferralCodeBonusInvited(models.Model):
    points = models.DecimalField(
        verbose_name=_('Баллы'),
        decimal_places=2,
        max_digits=12
    )

    def __str__(self):
        return f"{self.points}"

    def save(self, *args, **kwargs):
        if ReferralCodeBonusInvited.objects.exists() and not self.pk:
            raise ValidationError(_("Допускается только один экземпляр."))
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _('Баллы пользователя который пригласил')
        verbose_name_plural = _('Баллы пользователей которые пригласили')


class ReferralCodeBonus(models.Model):
    points = models.DecimalField(
        verbose_name=_('Баллы'),
        decimal_places=2,
        max_digits=12
    )

    def __str__(self):
        return f"{self.points}"

    def save(self, *args, **kwargs):
        if ReferralCodeBonus.objects.exists() and not self.pk:
            raise ValidationError(_("Допускается только один экземпляр."))
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _('Баллы за реферальный код')
        verbose_name_plural = _('Баллы за реферальный код')


class ReferralCode(models.Model):
    invites = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('Пригласитель'),
        related_name='invites'
    )
    invited = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('Приглашённый'),
        related_name='invited'
    )
    code = models.CharField(
        max_length=7,
        verbose_name=_('Пригласительный код')
    )
    created_date = models.DateTimeField(
        verbose_name=_('Дата создания'),
        auto_now_add=True
    )

    def clean(self):
        invites = self.invites
        invited = self.invited
        if self.invites.invitation_code != self.code:
            raise ValidationError({'Сообщение': _('Такой ссылки не существует')})

        elif self.invites == self.invited:
            raise ValidationError({'Сообщение': _('Вы не можете указывать свой пригласительньый код')})
        return super().clean()

    def __str__(self):
        return f'Пригласитель {self.invites}, Приглашённый {self.invited}'

    def save(self, *args, **kwargs):
        invites = self.invites
        invited = self.invited
        try:
            invited_bonus = ReferralCodeBonusInvited.objects.get().points
            invites_bonus = ReferralCodeBonus.objects.get().points
        except ReferralCodeBonusInvited.DoesNotExist:
            invited_bonus = Decimal('0')
        except ReferralCodeBonus.DoesNotExist:
            invites_bonus = Decimal('0')
        invites.balance = Decimal(str(invites.balance)) + Decimal(str(invites_bonus))
        invited.balance = Decimal(str(invited.balance)) + Decimal(str(invited_bonus))
        invites.save()
        invited.save()
        return super().save(*args, **kwargs)

    class Meta:
        verbose_name = _('Реферальный код')
        verbose_name_plural = _('Реферальный код')
        unique_together = ['invites', 'invited']


class BuyingAction(models.Model):
    user = models.ForeignKey(
        MyUser,
        on_delete=models.CASCADE,
        related_name='buying_actions_user',
        verbose_name=_('Пользователь')
    )
    action = models.ForeignKey(
        Action,
        on_delete=models.CASCADE,
        related_name='buying_actions',
        verbose_name=_('Акция')
    )
    created_date = models.DateTimeField(
        verbose_name=_('Дата создания'),
        auto_now_add=True
    )
    is_paid = models.BooleanField(
        verbose_name=_('Акция оплачена'),
        default=False
    )

    def save(self, *args, **kwargs):
        if not self.id:
            user = self.user
            action = self.action
            if action.price and action.is_paid:
                user.balance -= action.price
                user.save()
                self.is_paid = True
        super(BuyingAction, self).save(*args, **kwargs)

    def clean(self):
        if self.is_paid and self.action.price is None:
            raise ValidationError(_("Введите цену акции"))
        if self.is_paid and self.action.price < Decimal('0'):
            raise ValidationError(_("Цена акции не может быть меньше 0"))
        if self.is_paid and self.user.balance is None:
            raise ValidationError(_("У пользователя не задан баланс"))
        if self.is_paid and self.user.balance < self.action.price:
            raise ValidationError(_("На вашем счету недостаточно средств для оплаты этой акции"))

    def __str__(self):
        return str(self.user)

    class Meta:
        verbose_name = _('Покупка акции')
        verbose_name_plural = _('Покупка акций')


class WithdrawalRequests(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('Пользователь'),
    )
    total = models.DecimalField(
        verbose_name=_('Сумма вывода'),
        decimal_places=2,
        max_digits=12,
    )
    card_number = models.ForeignKey(
        'account.CardNumber',
        on_delete=models.CASCADE,
        verbose_name=_('Банковская карта')
    )
    status = models.PositiveSmallIntegerField(
        choices=(
            (1, _('В обработке')),
            (2, _('Выполнен')),
            (3, _('Отклонено'))
        ),
        verbose_name=_('Статус'),
        default=1
    )
    reject = models.TextField(
        verbose_name=_('Причина отказа'),
        null=True,
        blank=True
    )
    created_date = models.DateTimeField(
        verbose_name=_('Дата создания'),
        auto_now_add=True
    )

    def clean(self):
        user = self.user
        if user.balance < self.total:
            raise ValidationError(_('У вас недостаточно средств'))
        if not self.card_number.is_active:
            raise ValidationError(_('Выбранная карта не активна'))
        return super().clean()

    def save(self, *args, **kwargs):
        user = self.user
        if self.status == 2:
            user.balance -= self.total
            user.save()
        return super().save(*args, **kwargs)

    def __str__(self):
        return str(self.user)

    class Meta:
        verbose_name = _('Заявка на вывод денег')
        verbose_name_plural = _('Заявки на вывод денег')


class CheckQr(models.Model):
    STATUS_CHOICES = (
        (1, _('На проверке')),
        (2, _('Выполнен')),
        (3, _('Отклонен')),
    )
    user = models.ForeignKey(
        MyUser,
        on_delete=models.CASCADE,
        verbose_name=_('Пользователь'),
    )
    total = models.DecimalField(
        verbose_name=_('Сумма'),
        decimal_places=2,
        max_digits=12,
        default=0
    )
    check_creation_date = models.DateField(
        verbose_name=_('Дата создания чека'),
        default=datetime(year=2999, month=12, day=31),
        blank=True,
        null=True,
    )
    general_info = models.TextField(
        verbose_name=_('Общая информация'),
        blank=True,
        null=True
    )
    status = models.PositiveSmallIntegerField(
        choices=STATUS_CHOICES,
        default=1,
        verbose_name=_('Статус')
    )
    cashback = models.DecimalField(
        verbose_name=_('Кэшбэк'),
        decimal_places=2,
        max_digits=12,
        default=0
    )
    created_date = models.DateTimeField(
        verbose_name=_('Дата создания'),
        auto_now_add=True
    )

    def save(self, *args, **kwargs):
        if Check.objects.filter(general_info=self.general_info).exists():
            raise ValidationError({"Сообщение": "Такой чек уже существует"})
        if self.check_creation_date != timezone.now().date():
            self.status = 3
        else:
            self.status = 2
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.user)

    class Meta:
        verbose_name = _('Чек сделанный по QR')
        verbose_name_plural = _('Чеки сделанные по QR')
        ordering = ['-created_date']
