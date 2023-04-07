from django.urls import path, include
from .views import *


urlpatterns = [
    path('card_number_detail/<int:pk>/', CardNumberDetailView.as_view()),
    path('users/<int:pk>/', UserDeleteView.as_view()),
    path('register/', UserRegisterView.as_view()),
    path('profile-update/', UserProfileUpdateAPIView.as_view()),
    path('logout/', logout_view),
    path('resending_code_phone/', ResendingTheCodePhone.as_view()),
    path('resending_code_email/', ResendingTheCodeEmail.as_view()),
    path('reset_password_email/', ResetPasswordWithEmailView.as_view()),
    path('reset_password_phone/', ResetPasswordPhoneView.as_view()),
    path('profile/', UserProfileListView.as_view()),
    path('login/', LoginView.as_view()),
    path('agreement/', AgreementView.as_view()),
    path('card_number-list/', CardNumberListCreateView.as_view()),
    path('card_number-delete/<int:pk>/', CardNumberDeleteAPIView.as_view()),
    path('card_number-update/<int:pk>/', CardNumberUpdate.as_view()),
    path('country_and_city_list/', CountryAndCityViewList.as_view()),
    path('countries/<int:country_id>/cities/', CountryCityListAPIView.as_view()),
    path('activate-email/', EmailActivationView.as_view()),
    path('confirm-email/', ConfirmEmailView.as_view()),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.jwt')),
]
