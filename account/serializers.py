from rest_framework import serializers
from rest_framework.exceptions import ValidationError
import requests
from django.core.mail import send_mail
from random import randint
from app.models import Currency, ReferralCode, FeaturedUserAction, BuyingAction
from main.settings import EMAIL_HOST_USER
from .models import MyUser, Agreement, CardNumber, Country, City, EmailActive
from django.utils.translation import activate, gettext_lazy as _
from django.utils import translation
from django.conf import settings


class ResetEmailNumber(serializers.Serializer):
    email = serializers.EmailField(read_only=False)

    class Meta:
        model = MyUser
        fields = ("email",)


class EmailActivationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        if EmailActive.objects.filter(email=value, is_active=True).exists():
            raise serializers.ValidationError(_('Этот адрес электронной почты уже активирован'))
        return value


class ConfirmEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    code = serializers.CharField(max_length=4, required=True)

    def validate(self, data):
        email = data['email']
        code = data['code']
        if not EmailActive.objects.filter(email=email, code=code).exists():
            raise serializers.ValidationError({'Сообщение': _('Неверный код активации')})
        return data


class AgreementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agreement
        fields = ('agree_disagree',)


class AgreementRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agreement
        fields = ('title', 'description')


class UserDeleteSerializer(serializers.ModelSerializer):

    class Meta:
        model = MyUser
        fields = "__all__"


class UserRegistrationSerializer(serializers.ModelSerializer):
    referral_code = serializers.CharField(required=False)
    agreement = AgreementSerializer()

    class Meta:
        model = MyUser
        fields = ['phone_number', 'email', 'country', 'referral_code', 'agreement']

    def create(self, validated_data):
        country = validated_data.get('country')
        if country:
            currency = country.currencies.filter(is_active=True).first()
        else:
            currency = Currency.objects.filter(char_code='RUB', is_active=True).first()

        email = validated_data.get('email')
        phone_number = validated_data.get('phone_number')

        if email:
            passcode = str(randint(1000, 9999))
            send_mail('code', f'{passcode}', EMAIL_HOST_USER, [email, ], fail_silently=False)
        elif phone_number:
            response = requests.get(f"https://sms.ru/code/call?phone={phone_number}&ip=33.22.11.55&api_id=[AE3867AA-436F-A761-7257-85F5FC9031F8]&json=1")
            if response.ok:
                passcode = response.json().get("code")
            else:
                raise ValidationError({'Cообщение': _('Не удалось отправить код подтверждения')})
        else:
            raise ValidationError({'Cообщение': _('Должен быть email или phone_number')})

        user = MyUser.objects.create(
            email=email,
            phone_number=phone_number,
            country=country,
            city=validated_data.get('city'),
            date_of_birth=validated_data.get('date_of_birth'),
            currency=currency,
            password=passcode
        )

        referral_code = validated_data.get('referral_code')
        if referral_code:
            if not referral_code.isdigit() or len(referral_code) != 6:
                raise ValidationError({'Cообщение': _('Код приглашения должен состоять из 6 цифр')})
            invites = MyUser.objects.filter(invitation_code=referral_code).first()
            if invites is None:
                raise ValidationError({'Cообщение': _('Такого кода приглашение не существует')})
            ReferralCode.objects.create(invites=invites, invited=user, code=referral_code)
        return user

    def validate(self, data):
        if not data.get('email'):
            data['email'] = None
        phone_number = data.get('phone_number')
        if not data.get('email') and not phone_number:
            raise ValidationError(_('Должен быть email или phone_number'))
        agreement_data = data.get('agreement')
        if not agreement_data.get('is_accepted', True):
            raise serializers.ValidationError({'Cообщение': _('Вы должны принять пользовательское соглашение')})
        return data


class CardNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardNumber
        fields = "__all__"


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        from app.models import Company
        model = Company
        fields = ('id', 'name', 'has_action', 'action')


class FeaturedUserActionListSerializerAC(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    company = serializers.SerializerMethodField()
    action = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = FeaturedUserAction
        fields = '__all__'

    def get_company(self, obj):
        if obj.action and obj.action.companies.exists():
            return CompanySerializer(obj.action.companies.first()).data
        return None

    def get_action(self, obj):
        from app.serializers import ActionListSerializer
        return ActionListSerializer(obj.action).data

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.action.image:
            image = obj.action.image.url
            if request is not None:
                image = request.build_absolute_uri(image)
        else:
            image = ""
        return image


class BuyingActionSerializerAC(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    action = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = BuyingAction
        fields = "__all__"

    def get_buying_action(self, obj):
        buying_actions = obj.buying_action.all()
        if buying_actions.exists():
            return BuyingActionSerializerAC(buying_actions, many=True).data
        return None

    def get_company(self, obj):
        if obj.action and obj.action.companies.exists():
            return CompanySerializer(obj.action.companies.first()).data
        return None

    def get_action(self, obj):
        from app.serializers import ActionListSerializer
        return ActionListSerializer(obj.action).data

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.action.image:
            image = obj.action.image.url
            if request is not None:
                image = request.build_absolute_uri(image)
        else:
            image = ""
        return image


class UserProfileListSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    email = serializers.EmailField(required=True)
    card_number = CardNumberSerializer()
    featured_actions = FeaturedUserActionListSerializerAC(many=True)
    buying_action = BuyingActionSerializerAC(many=True)

    class Meta:
        model = MyUser
        fields = (
            'id',
            'email',
            'username',
            'phone_number',
            'date_of_birth',
            'country',
            'city',
            'balance',
            'level',
            'price_limit',
            'currency',
            'card_number',
            'invitation_code',
            'today_amount',
            'image_url',
            'image',
            'featured_actions',
            'buying_action',
            'language'
            )

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image:
            image = obj.image.url
            if request is not None:
                image = request.build_absolute_uri(image)
        else:
            image = ""
        return image


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    withdrawal_card = serializers.SerializerMethodField()

    class Meta:
        model = MyUser
        fields = (
            'user',
            'id',
            'email',
            'username',
            'phone_number',
            'date_of_birth',
            'country',
            'city',
            'balance',
            'level',
            'price_limit',
            'currency',
            'card_number',
            'invitation_code',
            'today_amount',
            'image',
            'withdrawal_card',
            'language',
        )

    def get_withdrawal_card(self, obj):
        if obj.card_number:
            return obj.card_number.withdrawal_card
        return None

    def get_image(self, obj):
        if obj.image:
            return obj.image.name
        else:
            return None

    def validate(self, attrs):
        if 'username' in attrs:
            username = attrs['username']
            if MyUser.objects.filter(username=username).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError({'Cообщение': 'Это имя пользователя уже занято.'})

        card_number = attrs.get('card_number')
        if card_number:
            card_number.withdrawal_card = True
            card_number.save()
            user = self.context['request'].user
            CardNumber.objects.filter(user=user).exclude(id=card_number.id).update(withdrawal_card=False)

        language = attrs.get('language')
        if language and language in dict(settings.LANGUAGES).keys():
            translation.activate(language)
            self.context['request'].LANGUAGE_CODE = language
            self.context['request'].user.language = language
            self.context['request'].user.save()

        return attrs

    def to_representation(self, instance):
        request = self.context.get('request')
        if request:
            language = request.GET.get('language', request.LANGUAGE_CODE)
            with translation.override(language):
                return super().to_representation(instance)
        return super().to_representation(instance)

    def __init__(self, *args, **kwargs):
        super(UserProfileUpdateSerializer, self).__init__(*args, **kwargs)
        user = self.context['request'].user
        self.fields['card_number'].queryset = CardNumber.objects.filter(user=user)


class CardNumberDeleteSerializer(serializers.Serializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = CardNumber
        fields = ('user', 'card_number', 'rel_user', 'id')


class CardNumberListSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = CardNumber
        fields = ('user', 'card_number', 'id', 'is_active', 'withdrawal_card')

    def __init__(self, *args, **kwargs):
        super(CardNumberListSerializer, self).__init__(*args, **kwargs)
        user = self.context['request'].user
        self.fields['card_number'].queryset = CardNumber.objects.filter(user=user)


class CardNumberCreateSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    rel_user = UserProfileListSerializer(source='user', read_only=True)
    withdrawal_card = serializers.SerializerMethodField()

    class Meta:
        model = CardNumber
        fields = ('user', 'card_number', 'rel_user', 'id', 'withdrawal_card')

    def get_withdrawal_card(self, obj):
        return obj.withdrawal_card if obj.withdrawal_card else False

    def __init__(self, *args, **kwargs):
        super(CardNumberCreateSerializer, self).__init__(*args, **kwargs)
        user = self.context['request'].user
        self.fields['card_number'].queryset = CardNumber.objects.filter(user=user)

    def save(self, **kwargs):
        is_first_card = self.Meta.model.objects.filter(user=self.validated_data['user']).count() == 0
        instance = super().save(**kwargs)
        if is_first_card:
            instance.user.card_number = instance
            instance.user.save()
        return instance


class CardNumberUpdateSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    rel_user = UserProfileListSerializer(source='user', read_only=True)

    class Meta:
        model = CardNumber
        fields = ('card_number', 'user', 'id', 'rel_user')


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(required=False)
    password = serializers.CharField(required=True)

    def validate(self, data):
        email = data.get('email')
        phone_number = data.get('phone_number')
        password = data.get('password')
        if not email and not phone_number:
            msg = _('Укажите email или телефон')
            raise serializers.ValidationError(msg)
        if email and phone_number:
            msg = _('Укажите только email или телефон, но не оба поля')
            raise serializers.ValidationError(msg)
        try:
            if email:
                users = MyUser.objects.filter(email=email)
                if phone_number:
                    users = users.exclude(phone_number='')
            elif phone_number:
                users = MyUser.objects.filter(phone_number=phone_number)
            else:
                msg = _('Укажите email или телефон')
                raise serializers.ValidationError(msg)
            user = users.get()
        except MyUser.DoesNotExist:
            msg = _('Неверные учетные данные')
            raise serializers.ValidationError(msg)
        except MyUser.MultipleObjectsReturned:
            msg = _('Ошибка базы данных: Несколько пользователей с одним email или телефоном')
            raise serializers.ValidationError(msg)
        data['user'] = user
        return data


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ('id', 'name')


class CountryAndCitySerializer(serializers.ModelSerializer):
    city_data = CitySerializer(many=True)

    class Meta:
        model = Country
        fields = ('name', 'id', 'city_data')
