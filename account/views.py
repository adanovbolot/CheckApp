from celery import shared_task
from django.http import Http404
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.generics import ListAPIView, get_object_or_404, DestroyAPIView, \
    RetrieveAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from .serializers import *
from django.contrib.auth import login, logout
import requests
from .models import MyUser, Agreement, CardNumber, Country
from random import randint
from django.contrib.auth import get_user_model
from datetime import timedelta
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from django.conf import settings
from .models import EmailActive
from .serializers import EmailActivationSerializer, ConfirmEmailSerializer
from django.shortcuts import get_object_or_404
from .utils import generate_confirmation_code, send_email
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class EmailActivationView(APIView):
    serializer_class = EmailActivationSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if serializer.is_valid():
            email = serializer.validated_data['email']
            code = generate_confirmation_code(email)
            user = request.user
            email_activation = EmailActive.objects.create(email=email, code=code, user=user)
            send_email(email, code)
            return Response({'Сообщение': _('Код активации отправлен на вашу электронную почту')},
                            status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConfirmEmailView(APIView):
    serializer_class = ConfirmEmailSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            email_activation = EmailActive.objects.filter(email=email).first()
            if not email_activation:
                return Response({'Сообщение': _('Электронная почта не найдена')},
                                  status=status.HTTP_404_NOT_FOUND)
            if email_activation.is_active:
                return Response({'Сообщение': _('Электронная почта уже активирована')},
                                  status=status.HTTP_400_BAD_REQUEST)
            code = serializer.validated_data['code']
            if not email_activation.check_code(code):
                return Response({'Сообщение': _('Неверный код')},
                                status=status.HTTP_400_BAD_REQUEST)
            email_activation.is_active = True
            email_activation.save()
            return Response({'Сообщение': _('Электронная почта успешно активирована')},
                            status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserDeleteView(generics.DestroyAPIView):
    queryset = MyUser.objects.all()
    serializer_class = UserDeleteSerializer

    def get(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.serializer_class(user)
        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        if user.date_of_registration:
            raise ValidationError(_('Пользователь уже удален'))
        user.date_of_registration = timezone.now() + timedelta(days=30)
        user.save()
        logout(request)
        return super().delete(request, *args, **kwargs)


@shared_task
def delete_user_task(user_id):
    user = MyUser.objects.get(id=user_id)
    if not user.date_of_registration:
        return
    if user.avatar:
        user.avatar.delete(save=False)
    user.delete()


@api_view(['POST'])
@csrf_exempt
def logout_view(request):
    user_id = request.data.get('id')
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({'Сообщение': _('Пользователь с таким id не найден')},
                          status=status.HTTP_404_NOT_FOUND)
    logout(request)
    return Response({'Сообщение': _('Пользователь успешно вышел из системы')})


class ResetPasswordPhoneView(APIView):
    def post(self, request, format=None):
        phone_number = request.data.get('phone_number', None)
        if not phone_number:
            return Response({'Сообщение': _('Укажите номер телефона')},
                            status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(phone_number=phone_number).first()
        if not user:
            return Response({'Сообщение': _('Пользователь с таким номером телефона не существует')},
                            status=status.HTTP_404_NOT_FOUND)
        new_password = str(randint(1000, 9999))
        api_key = 'AE3867AA-436F-A761-7257-85F5FC9031F8'
        response = requests.get(
            f'https://sms.ru/code/call?phone={phone_number}&ip=33.22.11.55&api_id=[{api_key}]&json=1')
        if not response.ok:
            return Response({'Сообщение': _('Не удалось отправить код подтверждения')},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        user.set_password(new_password)
        user.save()
        return Response({'Сообщение': _('Пароль успешно изменен ожидайте звонка')},
                        status=status.HTTP_200_OK)


class ResetPasswordWithEmailView(generics.CreateAPIView):
    serializer_class = ResetEmailNumber

    def create(self, request, *args, **kwargs):
        email = request.data.get('email', None)
        if not email:
            return Response({'Сообщение': _('Укажите email')},
                            status=status.HTTP_400_BAD_REQUEST)
        user = MyUser.objects.filter(email=email).first()
        if not user:
            return Response({'Сообщение': _('Пользователь с таким email не существует')},
                            status=status.HTTP_404_NOT_FOUND)
        new_password = str(randint(1000, 9999))
        subject = _('Сброс пароля')
        message = _(f'Ваш новый пароль: {new_password}')
        from_email = settings.EMAIL_HOST_USER
        to_email = [email]
        send_mail(subject, message, from_email, to_email, fail_silently=False)
        user.set_password(new_password)
        user.save()
        return Response({'Сообщение': _('Новый пароль отправлен на вашу электронную почту')},
                        status=status.HTTP_200_OK)


class ResendingTheCodePhone(APIView):
    def post(self, request, format=None):
        phone_number = request.data.get('phone_number', None)
        if not phone_number:
            return Response({'Сообщение': _('Укажите номер телефона')},
                            status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(phone_number=phone_number).first()
        if not user:
            return Response({'Сообщение': _('Пользователь с таким номером телефона не существует')},
                            status=status.HTTP_404_NOT_FOUND)
        new_password = str(randint(1000, 9999))
        api_key = 'AE3867AA-436F-A761-7257-85F5FC9031F8'
        response = requests.get(
            f'https://sms.ru/code/call?phone={phone_number}&ip=33.22.11.55&api_id=[{api_key}]&json=1')
        if not response.ok:
            return Response({'Сообщение': _('Не удалось отправить код подтверждения')},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        user.set_password(new_password)
        user.save()
        return Response({'Сообщение': _('Пароль успешно отправлен ожидайте звонка')},
                        status=status.HTTP_200_OK)


class ResendingTheCodeEmail(generics.CreateAPIView):
    serializer_class = ResetEmailNumber

    def create(self, request, *args, **kwargs):
        email = request.data.get('email', None)
        if not email:
            return Response({'Сообщение': _('Укажите email')},
                            status=status.HTTP_400_BAD_REQUEST)
        user = MyUser.objects.filter(email=email).first()
        if not user:
            return Response({'Сообщение': _('Пользователь с таким email не существует')},
                            status=status.HTTP_404_NOT_FOUND)
        new_password = str(randint(1000, 9999))
        subject = _('Ваш код для активации')
        message = _(f'Ваш пароль: {new_password}')
        from_email = settings.EMAIL_HOST_USER
        to_email = [email]
        send_mail(subject, message, from_email, to_email, fail_silently=False)
        user.set_password(new_password)
        user.save()
        return Response({'Сообщение': _('Пароль отправлен на вашу электронную почту')},
                        status=status.HTTP_200_OK)


class CardNumberListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = CardNumber.objects.all()

    def get_queryset(self):
        return CardNumber.objects.filter(user=self.request.user.id, is_active=True)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CardNumberCreateSerializer
        elif self.request.method == 'GET':
            return CardNumberListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        user_cards_count = CardNumber.objects.filter(user=self.request.user).count()
        if user_cards_count == 1:
            card = serializer.instance
            card.withdrawal_card = True
            card.save()
        message = _('Новая карта была успешно добавлена.')
        return Response({'Сообщение': message, 'data': serializer.data}, status=status.HTTP_201_CREATED,
                        headers=headers)

    def perform_create(self, serializer):
        user = self.request.user
        card = serializer.save(user=user)
        has_other_cards = CardNumber.objects.filter(user=user).exclude(pk=card.pk).exists()
        if not has_other_cards:
            card.withdrawal_card = True
            card.save()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if not queryset:
            return Response({'Сообщение': _('Карты не найдены')}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(queryset, many=True)
        return Response({'data': serializer.data})


class CardNumberDeleteAPIView(DestroyAPIView):
    serializer_class = CardNumberDeleteSerializer
    permission_classes = [IsAuthenticated]
    queryset = CardNumber.objects.all()

    def get_queryset(self):
        return CardNumber.objects.filter(user=self.request.user)

    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        is_active = request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance:
            self.perform_destroy(instance)
            return Response({"Сообщение": _("Карта с номером {} успешно удалена").format(instance.card_number)})
        else:
            return Response({"Сообщение": _("Карта не найдена")}, status=status.HTTP_404_NOT_FOUND)


class CardNumberUpdate(APIView):
    def get_object(self, pk):
        return get_object_or_404(CardNumber, user=self.request.user.id, pk=pk)

    def get(self, request, pk):
        card_number = self.get_object(pk)
        serializer = CardNumberUpdateSerializer(card_number)
        return Response({'card_number': serializer.data, 'Сообщение': _('Информация о карте успешно получена.')},
                        status=status.HTTP_200_OK)

    def put(self, request, pk):
        card_number = self.get_object(pk)
        serializer = CardNumberUpdateSerializer(card_number, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({'Сообщение': _('Карта успешно обновлена')}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CardNumberDetailView(RetrieveAPIView):
    queryset = CardNumber.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = CardNumberSerializer

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except Http404:
            return Response({'status': _('ошибка'), 'Сообщение': _('Номер карты не найден')},
                            status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(instance)
        return Response({'status': _('Успешно'), 'data': serializer.data, 'exists': True}, status=status.HTTP_200_OK)


class AgreementView(ListAPIView):
    queryset = Agreement.objects.all()
    serializer_class = AgreementRegisterSerializer


class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            login(request, user)
            user.is_verified = True
            user.save()
            return Response({'Сообщение': _('Успешная авторизация')}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserRegisterView(generics.ListCreateAPIView):
    serializer_class = UserRegistrationSerializer
    queryset = MyUser.objects.all()

    def create(self, request, *args, **kwargs):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        response = requests.get(
            f'https://api.ipgeolocation.io/ipgeo?apiKey=e7c3481d7c884c6da1fbaf31ce615741&ip={ip}'
        ).json()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {'message': _('Пользователь успешно создан'), 'user': serializer.data},
            status=status.HTTP_201_CREATED,
            headers=headers
        )


class UserProfileListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileListSerializer

    def get_queryset(self):
        user_id = self.request.user.id
        return MyUser.objects.filter(id=user_id)


class UserProfileUpdateAPIView(UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileUpdateSerializer
    queryset = MyUser.objects.all()

    def get_object(self):
        return self.request.user

    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"Сообщение": _("Профиль успешно обновлен"), "data": serializer.data},
                        status=status.HTTP_200_OK)


class CountryAndCityViewList(ListAPIView):
    queryset = Country.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = CountryAndCitySerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if not queryset.exists():
            return Response({'Сообщение': _('Страны не найдены')}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class CountryCityListAPIView(RetrieveAPIView):
    serializer_class = CountryAndCitySerializer
    queryset = Country.objects.all()

    def get(self, request, *args, **kwargs):
        country_id = self.kwargs['country_id']
        try:
            country = self.queryset.get(id=country_id)
        except Country.DoesNotExist:
            return Response({'Сообщение': _('Страна не найдена')}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(country)
        return Response(serializer.data)
