from django.http import Http404
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.generics import ListAPIView, ListCreateAPIView, CreateAPIView, RetrieveDestroyAPIView, \
    RetrieveAPIView
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes
from .serializers import *
from account.models import *
from rest_framework.pagination import PageNumberPagination
import django_filters
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, mixins
from django.utils.translation import gettext_lazy as _
from rest_framework.decorators import api_view
from rest_framework.response import Response
from main.celery import process_check
from rest_framework import status


class CsrfExemptMixin(object):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(CsrfExemptMixin, self).dispatch(*args, **kwargs)


class CurrencyListView(APIView):
    queryset = Currency.objects.filter(is_active=True)

    def get(self, request):
        currencies = self.queryset.all()
        if not currencies:
            message = {'Сообщение': _('Активные валюты не найдены')}
            return Response(message, status=status.HTTP_404_NOT_FOUND)
        serializer = CurrencySerializer(currencies, many=True)
        message = {'Сообщение': _('Объект успешно найден')}
        return Response({'data': serializer.data, **message}, status=status.HTTP_200_OK)


class FeaturedUserActionCreateView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = FeaturedUserAction.objects.all()
    serializer_class = FeaturedUserActionCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        data = {'Сообщение': _('Добавлено в избранные.')}
        return Response(data, status=status.HTTP_201_CREATED)


class FeaturedUserActionListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = FeaturedUserAction.objects.all()
    serializer_class = FeaturedUserActionListSerializer

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"Сообщение": _("Учетные данные не были предоставлены.")},
                            status=status.HTTP_401_UNAUTHORIZED)
        return super().get(request, *args, **kwargs)


class FeaturedUserActionDeleteView(RetrieveDestroyAPIView):
    serializer_class = FeaturedUserActionListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return FeaturedUserAction.objects.filter(user=user)

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        self.perform_destroy(instance)
        message = {'Сообщение': _('Объект успешно удален.'), 'data': serializer.data}
        return Response(message, status=status.HTTP_200_OK)


class CheckQrFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=CheckQr.STATUS_CHOICES)

    class Meta:
        model = Check
        fields = ['status']


class CheckFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=Check.STATUS_CHOICES)

    class Meta:
        model = Check
        fields = ['status']


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_query_param = 'page'


@api_view(['GET'])
def check_and_check_qr_list_view(request):
    queryset_check = Check.objects.filter(user=request.user.id).order_by('-created_date')
    queryset_check_qr = CheckQr.objects.filter(user=request.user.id).order_by('-created_date')
    filter_check = CheckFilter(request.GET, queryset=queryset_check)
    filter_check_qr = CheckQrFilter(request.GET, queryset=queryset_check_qr)
    check_serializer = CheckListSerializer(filter_check.qs.all(), many=True, context={'request': request})
    check_qr_serializer = CheckQrListSerializer(filter_check_qr.qs.all(), many=True, context={'request': request})
    data = check_serializer.data + check_qr_serializer.data
    paginator = CustomPagination()
    paginated_data = paginator.paginate_queryset(data, request)
    return paginator.get_paginated_response(paginated_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_and_check_qr_detail_view(request, user_id):
    status = request.GET.get('status', '')
    queryset_check = Check.objects.filter(user=user_id).order_by('-created_date')
    queryset_check_qr = CheckQr.objects.filter(user=user_id).order_by('-created_date')
    if status:
        queryset_check = queryset_check.filter(status=status)
        queryset_check_qr = queryset_check_qr.filter(status=status)
    check_serializer = CheckListSerializer(queryset_check[:2], many=True, context={'request': request})
    check_qr_serializer = CheckQrListSerializer(queryset_check_qr[:2], many=True, context={'request': request})
    data = check_serializer.data + check_qr_serializer.data
    paginator = CustomPagination()
    paginated_data = paginator.paginate_queryset(data, request)
    return paginator.get_paginated_response(paginated_data)


class SlideListView(ListAPIView):
    queryset = Slide.objects.all().order_by('ordering')
    serializer_class = SlideListSerializer


class LevelPriceView(ListAPIView):
    queryset = LevelPrice.objects.all().order_by('level')
    serializer_class = LevelPriceSerializer

    def list(self, request, *args, **kwargs):
        try:
            response = super().list(request, *args, **kwargs)
            return response
        except Exception as e:
            return Response({'Сообщение': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class LevelPaymentCreateView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LevelPaymentCreateSerializer

    def get_queryset(self):
        return LevelPayment.objects.filter(user=self.request.user.id)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({'Сообщение': _('Уровень платежа успешно создан'), 'data': serializer.data},
                        status=status.HTTP_201_CREATED, headers=headers)


class ReferralCodeCreateView(CreateAPIView):
    serializer_class = ReferralCodeCreateSerializer


@api_view(['GET'])
def home_page_list(request):
    if request.method == 'GET':
        action = Action.objects.filter(is_active=True, country=request.user.country)
        other = Check.objects.filter(user=request.user.id)

        action_serializer = ActionListSerializer(action, many=True, context={'request': request})
        other_serializer = HomePageListSerializer(other, many=True, context={'request': request})
        data = action_serializer.data + other_serializer.data
        return Response(data)


class CheckScannerCreateView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CheckScannerSerializer

    def get_queryset(self):
        return Check.objects.all()

    def perform_create(self, serializer):
        instance = serializer.save(using='default')
        image_path = instance.image.path
        task = process_check.delay(image_path, instance.id)

        return Response({
            'task_id': task.id,
            'status': task.status,
            'result': task.result,
            'message': 'Задача запущена успешно. Чек на обработке.'
        }, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        instance = serializer.save()
        if instance.processed:
            updated_serializer = CheckScannerSerializer(instance=instance)
            return Response(updated_serializer.data)
        return Response(serializer.data)


class CheckScannerDetailView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CheckScannerSerializer
    lookup_field = 'id'

    def get_queryset(self):
        user = self.request.user
        return Check.objects.filter(user=user)

    def get_object(self):
        queryset = self.get_queryset()
        if not self.kwargs.get('id'):
            latest_check = queryset.filter(processed=True).last()
            if latest_check:
                return latest_check
        obj = super().get_object()
        if obj.user != self.request.user:
            raise PermissionDenied()
        return obj


class CheckQrListCreateViews(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CheckQrListSerializer

    def get_queryset(self):
        return CheckQr.objects.filter(user=self.request.user.id)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CheckQrCreateSerializer
        elif self.request.method == 'GET':
            return CheckQrListSerializer

    def perform_create(self, serializer):
        instance = serializer.save()
        user = self.request.user
        total = instance.total
        currency = user.currency.char_code
        status = instance.status
        if currency == 'USD':
            converted_total = total
        else:
            try:
                currency_obj = Currency.objects.get(char_code='USD', is_active=True)
            except Currency.DoesNotExist:
                raise serializers.ValidationError({'message': _('Не удается найти активную валюту в долларах США.')})
            actual_value = currency_obj.actual_value
            if currency == 'RUB':
                converted_total = total / actual_value
            elif currency == 'EUR':
                converted_total = total * actual_value
            else:
                raise serializers.ValidationError({'message': _('Недопустимая валюта.')})

        cashback_percentage = PercentageCashbackCheck.objects.first().points
        cashback_amount = converted_total * cashback_percentage / 100
        if status != 2:
            return
        if cashback_amount > user.price_limit:
            instance.status = 1
            instance.save()
            raise serializers.ValidationError({'message': _('Превышен лимит для кэшбэка')})
        user.balance += cashback_amount
        user.save()
        data = {'message': _('Успешно создано'), 'data': serializer.data}
        return Response(data)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        response.data = ({'Сообщение': _('Успешно создано')}, status.HTTP_201_CREATED)
        return response


class ActionFilter(django_filters.FilterSet):
    STATUS_CHOICES = (
        (1, _('Акции')),
        (2, _('Cпецпредложения')),
    )

    status = django_filters.ChoiceFilter(
        choices=STATUS_CHOICES,
        label=_('Статус'),
        method='filter_status'
    )

    def filter_status(self, queryset, name, value):
        if value:
            queryset = queryset.filter(translations__status=value).distinct()
        return queryset

    class Meta:
        model = Action
        fields = ['status']


class ActionListCreateView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CompanyListSerializer
    pagination_class = PageNumberPagination
    queryset = Company.objects.filter(has_action=True)
    filter_class = ActionFilter

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(action__status=status_filter)
        user_country = self.request.user.country
        queryset = queryset.filter(action__country=user_country, action__is_active=True)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        if not queryset.exists():
            raise NotFound({'Сообщение': _('Компании с акциями не найдены')})
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(queryset, request)
        serializer = self.get_serializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)


class CityListView(ListAPIView):
    queryset = City.objects.all()
    serializer_class = CityListSerializer

    def get_queryset(self):
        try:
            queryset = super().get_queryset()
        except Exception as e:
            return Response({'Сообщение': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return queryset


class QuestionAnswerListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = QuestionAnswer.objects.all()
    serializer_class = QuestionAnswerSerializer

    def list(self, request, *args, **kwargs):
        try:
            response = super().list(request, *args, **kwargs)
            return response
        except Exception as e:
            return Response({'Сообщение': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class BuyingActionViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = BuyingActionSerializerCreate
    from rest_framework.decorators import action

    def perform_create(self, serializer):
        user = self.request.user
        action = serializer.validated_data['action']
        if action.price and action.is_paid:
            if user.balance < action.price:
                raise serializers.ValidationError({"Сообщение": _('Недостаточно средств на счету пользователя.')})
            user.balance -= action.price
            user.save()
            serializer.save(user=user, is_paid=True)
            return Response({'Сообщение': _('Акция успешно оплачена.')}, status=status.HTTP_201_CREATED)
        serializer.save(user=user)
        return Response({'Сообщение': _('Акция успешно добавлена в список покупок.')}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({'Сообщение': _('Покупка акции прошла успешно.')}, status=status.HTTP_201_CREATED, headers=headers)


class BuyingActionListView(ListAPIView):
    serializer_class = BuyingActionListSerializer

    def get_queryset(self):
        user = self.request.user
        if not user:
            raise NotFound(_('Пользователь не найден'))
        queryset = BuyingAction.objects.filter(user=user.id, is_paid=True)
        if not queryset:
            raise NotFound(_('Оплаченные акции не найдены'))
        return queryset

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        if not response.data:
            response.data = {"Сообщение": _("Оплаченные акции не найдены")}
        return response


class BuyingActionDetail(RetrieveDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BuyingActionSerializer
    queryset = BuyingAction.objects.all()

    def get_queryset(self):
        queryset = BuyingAction.objects.filter(user=self.request.user.id, is_paid=True)
        return queryset

    def delete(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except Http404:
            return Response({'Сообщение': _('Запись не найдена')}, status=status.HTTP_404_NOT_FOUND)
        self.perform_destroy(instance)
        return Response({'Сообщение': _('Запись успешно удалена')}, status=status.HTTP_204_NO_CONTENT)


class WithdrawalRequestsCreateView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WithdrawalRequestsCreateSerializer

    def get_queryset(self):
        return WithdrawalRequests.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        card_number = serializer.validated_data['card_number']
        user_cards = CardNumber.objects.filter(user=self.request.user)
        for card in user_cards:
            if card == card_number:
                card.withdrawal_card = True
            else:
                card.withdrawal_card = False
            card.save()
        instance = serializer.save()
        data = serializer.data
        return Response(data, status=status.HTTP_201_CREATED)


class CountryListView(ListAPIView):
    queryset = Country.objects.all()
    serializer_class = CountryListSerializer

    def get_queryset(self):
        try:
            queryset = super().get_queryset()
        except Exception as e:
            return Response({'Сообщение': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return queryset


class CategoriesSupportViewList(ListAPIView):
    queryset = CategoriesSupport.objects.all()
    serializer_class = CategoriesSupportSerializerList
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class SupportListView(ListAPIView):
    serializer_class = SupportListSerializer
    permission_classes = [IsAuthenticated]
    queryset = Support.objects.all()

    def get_queryset(self):
        try:
            return Support.objects.filter(user=self.request.user.id).order_by('-created_date')
        except Exception as e:
            return Response({'Сообщение': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        try:
            serializer.save(user=self.request.user)
        except Exception as e:
            return Response({'Сообщение': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AnswerQuestionViewListCreate(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AnswerQuestionSerializer
    queryset = AnswerQuestion.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({'Сообщение': _('Отправлено в службу поддержки')}, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        serializer.save()

    def get_object(self):
        try:
            obj = super().get_object()
        except Http404:
            raise Http404(_('Запрошенный объект не найден.'))
        return obj

    def handle_exception(self, exc):
        if isinstance(exc, Http404):
            return Response({'Сообщение': str(exc)}, status=status.HTTP_404_NOT_FOUND)
        return super().handle_exception(exc)
