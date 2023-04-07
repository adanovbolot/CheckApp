from .models import *
from account.models import *
from account.serializers import UserProfileListSerializer
from decimal import Decimal
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Check
from django.utils.translation import gettext_lazy as _
from datetime import datetime
from datetime import date
from django.db.models.signals import pre_save
from django.dispatch import receiver


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ('id', 'char_code', 'actual_value')


class CategoriesSupportSerializerList(serializers.ModelSerializer):

    class Meta:
        model = CategoriesSupport
        fields = ('id', 'title_category',)


class QuestionAnswerSerializer(serializers.ModelSerializer):

    class Meta:
        model = QuestionAnswer
        fields = "__all__"


class UserNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ('id', 'username', 'balance', 'price_limit', 'level')


class SlideListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Slide
        fields = ('id', 'file', 'ordering')


class AnswerQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerQuestion
        fields = ('id', 'question', 'created_date', 'categories_support')


class SupportListSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    category_support = CategoriesSupportSerializerList()
    answer = serializers.ReadOnlyField(source='answer_question.answer')

    class Meta:
        model = Support
        fields = ('user', 'description', 'id', 'answer', 'category_support')


class LevelPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LevelPrice
        fields = ('id', 'level', 'title', 'price', 'limit', 'created_date', 'is_active')


class LevelPaymentListSerializer(serializers.ModelSerializer):
    class Meta:
        model = LevelPayment
        fields = ('id', 'level', 'created_date', 'get_status_display')


class LevelPaymentCreateSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    level_payments = UserProfileListSerializer(source='user', read_only=True)

    class Meta:
        model = LevelPayment
        fields = ('user', 'level', 'level_payments', 'id')

    def validate(self, data):
        user = data['user']
        level = data['level']
        current_level = user.level
        if current_level is None:
            raise serializers.ValidationError({"Сообщение": _('У вас нет уровня')})
        if user.level >= level.level:
            if user.level == 1:
                raise serializers.ValidationError(
                    {"Сообщение": _('Вы уже получили первый уровень')})
            raise serializers.ValidationError(
                {"Сообщение": _('Ваш уровень больше или равен уровню, который вы хотите купить')})
        if current_level != level.level - 1:
            raise serializers.ValidationError(
                {"Сообщение": _("Вы не можете купить этот уровень, пока не достигнете предыдущего уровня")})
        if LevelPayment.objects.filter(user=user, level=level).exists():
            raise serializers.ValidationError({"Сообщение": _('Вы уже купили этот уровень')})
        level_price = level.price
        if user.balance < level_price:
            raise serializers.ValidationError({"Сообщение": _('У вас недостаточно средств')})
        return data

    def create(self, validated_data):
        level_payment = LevelPayment(**validated_data)
        level_payment.clean()
        level_payment.save()
        return level_payment


class ReferralCodeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralCode
        fields = ('code',)

    def create(self, validated_data):
        referal = ReferralCode.objects.create(
            invites=validated_data['invites'],
            invited=self.context['request'].user,
            code=validated_data['code']
        )
        return referal

    def validate(self, data):
        invites = MyUser.objects.filter(invitation_code=data['code']).first()
        if invites is None:
            raise ValidationError(_({'Сообщение': 'Нет'}))
        invited = self.context['request'].user
        code = data['code']
        if invites.invitation_code != code:
            raise serializers.ValidationError({'Сообщение': _('Такого кода приглашение не существует')})
        elif invites == invited:
            raise serializers.ValidationError({'Сообщение': _('Вы не можете использовать свой собственный код приглашения')})
        data['invites'] = invites
        return data


class CheckListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Check
        fields = (
            'status',
            'image',
            'created_date',
            'total',
            'get_status_display',
            'check_creation_date',
        )


class StockCategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockCategory
        fields = '__all__'


class ActionListSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    section = StockCategoryListSerializer()
    image_url = serializers.SerializerMethodField()

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image:
            image = obj.image.url
            if request is not None:
                image = request.build_absolute_uri(image)
        else:
            image = ""
        return image

    class Meta:
        model = Action
        fields = '__all__'


class CompanyListSerializer(serializers.ModelSerializer):
    action = ActionListSerializer()

    class Meta:
        model = Company
        fields = "__all__"


class FeaturedUserActionCreateSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    action = serializers.PrimaryKeyRelatedField(queryset=Action.objects.all())

    class Meta:
        model = FeaturedUserAction
        fields = '__all__'

    def save(self, **kwargs):
        featured_actions = super().save(**kwargs)
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user = request.user
            user.featured_actions.add(featured_actions)
        return featured_actions

    def validate(self, attrs):
        user = attrs['user']
        action = attrs['action']
        existing_instance = FeaturedUserAction.objects.filter(
            user=user,
            action=action
        ).first()
        if existing_instance:
            raise ValidationError({'Сообщение': _('Такая акция уже есть в избранных.')})
        return super().validate(attrs)


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ('id', 'name', 'has_action', 'action')


class FeaturedUserActionListSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    company = serializers.SerializerMethodField()
    action = ActionListSerializer()

    class Meta:
        model = FeaturedUserAction
        fields = '__all__'

    def get_company(self, obj):
        if obj.action and obj.action.companies.exists():
            return CompanySerializer(obj.action.companies.first()).data
        return None


class HomePageListSerializer(serializers.ModelSerializer):
    user = UserNameSerializer()

    class Meta:
        model = Check
        fields = ('user', 'created_date', 'total', 'get_status_display')


class BuyingActionSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    action = ActionListSerializer()

    class Meta:
        model = BuyingAction
        fields = "__all__"


class BuyingActionSerializerCreate(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = BuyingAction
        fields = ('action', 'user')

    def save(self, **kwargs):
        buying_action = super().save(**kwargs)
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user = request.user
            user.buying_action.add(buying_action)
        return buying_action

    def validate_action(self, value):
        if value.price is None:
            raise serializers.ValidationError({"Сообщение": _('Укажите цену для данной акции.')})
        if value.price < Decimal('0'):
            raise serializers.ValidationError({"Сообщение": _('Цена акции не может быть отрицательной.')})
        return value

    def validate(self, attrs):
        user = attrs['user']
        action = attrs['action']
        existing_instance = BuyingAction.objects.filter(
            user=user,
            action=action
        ).first()
        if existing_instance:
            raise serializers.ValidationError({"Сообщение": _('Такая акция уже есть в списке покупок.')})
        return attrs


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ('id', 'name')


class CityListSerializer(serializers.ModelSerializer):
    country = CountrySerializer()

    class Meta:
        model = City
        fields = '__all__'


class QuestionAnswerListSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionAnswer
        fields = '__all__'


class BuyingActionListSerializer(serializers.ModelSerializer):
    action = ActionListSerializer()

    class Meta:
        model = BuyingAction
        fields = '__all__'


class WithdrawalRequestsCreateSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    card_number = serializers.PrimaryKeyRelatedField(
        queryset=CardNumber.objects.all(),
        required=True
    )
    status = serializers.IntegerField(read_only=True, default=1)
    message = serializers.CharField(read_only=True, default=_('Запрос на вывод средств успешно прошло'))

    class Meta:
        model = WithdrawalRequests
        fields = ('user', 'total', 'card_number', 'status', 'message')

    def get_default_card_number(self, user):
        try:
            return CardNumber.objects.get(user=user, withdrawal_card=True)
        except CardNumber.DoesNotExist:
            return None

    def validate_card_number(self, card_number):
        if card_number is None:
            user = self.context['request'].user
            default_card_number = self.get_default_card_number(user)
            if default_card_number is None:
                raise serializers.ValidationError(_('Не найдено карт для вывода'))
            return default_card_number
        return card_number

    def create(self, validated_data):
        user = validated_data['user']
        total = validated_data['total']
        card_number = validated_data['card_number']

        if user.balance < total:
            raise serializers.ValidationError(_('У вас недостаточно средств для создания запроса на вывод'))

        try:
            withdrawal_request = WithdrawalRequests.objects.create(
                user=user,
                total=total,
                card_number=card_number,
                status=2
            )
            user.balance -= total
            user.save()
        except Exception as e:
            raise serializers.ValidationError(str(e))
        return withdrawal_request

    def __init__(self, *args, **kwargs):
        super(WithdrawalRequestsCreateSerializer, self).__init__(*args, **kwargs)
        user = self.context['request'].user
        self.fields['card_number'].queryset = CardNumber.objects.filter(user=user)


class WithdrawalRequestsListSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawalRequests
        fields = '__all__'


class CheckQrListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CheckQr
        fields = ('user', 'total', 'check_creation_date', 'general_info', 'status')


class CheckScannerSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    general_info = serializers.CharField(required=False)
    image = serializers.ImageField()
    total = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    check_creation_date = serializers.DateField(required=False)
    status = serializers.ChoiceField(choices=Check.STATUS_CHOICES, read_only=True)
    message = serializers.CharField(read_only=True)

    class Meta:
        model = Check
        fields = ('image', 'user', 'general_info', 'check_creation_date', 'total', 'status', 'message')

    def create(self, validated_data):
        validated_data['check_creation_date'] = date.today()
        validated_data['status'] = Check.STATUS_CHOICES[0][0]
        using = validated_data.pop('using', None)
        if using:
            instance = Check.objects.using(using).create(**validated_data)
        else:
            instance = Check.objects.create(**validated_data)

        instance.message = "Чек обрабатывается"
        return instance


class CheckQrCreateSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    status = serializers.BooleanField(read_only=True)

    class Meta:
        model = CheckQr
        fields = ('user', 'total', 'check_creation_date', 'general_info', 'status', 'id')

    def parse_general_info(self, general_info):
        data = {}
        for param in general_info.split('&'):
            key, value = param.split('=')
            if key == 't':
                data['check_creation_date'] = datetime.strptime(value[:8], '%Y%m%d').date()
            elif key == 's':
                data['total'] = Decimal(value.strip())
        return data

    def validate(self, attrs):
        general_info = attrs.get('general_info')
        if CheckQr.objects.filter(general_info=general_info).exists():
            raise serializers.ValidationError({'Сообщение': _('Данный чек уже был создан.')})
        if general_info:
            parsed_data = self.parse_general_info(general_info)
            if 'total' in parsed_data:
                attrs['total'] = parsed_data['total']
            if 'check_creation_date' in parsed_data:
                attrs['check_creation_date'] = parsed_data['check_creation_date']
        if 'total' in attrs and 'check_creation_date' in attrs:
            if attrs['check_creation_date'] != datetime.today().date():
                raise serializers.ValidationError({'Сообщение': _('Ваш чек устарел')})
        attrs['status'] = 2
        return attrs


class CountryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = '__all__'
