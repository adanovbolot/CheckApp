from django.urls import path, include
from . import views


urlpatterns = [
    path('check-scanner/<int:id>/', views.CheckScannerDetailView.as_view(), name='check-scanner-detail'),
    path('buying-actions/', views.BuyingActionViewSet.as_view({'post': 'create'}), name='buying-actions'),
    path('answer_question/', views.AnswerQuestionViewListCreate.as_view()),
    path('currency_list/', views.CurrencyListView.as_view()),
    path('slides/', views.SlideListView.as_view()),
    path('support/', views.SupportListView.as_view()),
    path('category_support/', views.CategoriesSupportViewList.as_view()),
    path('level-price/', views.LevelPriceView.as_view()),
    path('buying-a-level/', views.LevelPaymentCreateView.as_view()),
    path('referral_code/', views.ReferralCodeCreateView.as_view()),
    path('check-create/', views.CheckScannerCreateView.as_view()),
    path('index/', views.home_page_list),
    path('action-list/', views.ActionListCreateView.as_view()),
    path('city-list/', views.CityListView.as_view()),
    path('purchased-shares', views.BuyingActionListView.as_view()),
    path('action-buy-detail/<int:pk>/', views.BuyingActionDetail.as_view()),
    path('money-withdrawal', views.WithdrawalRequestsCreateView.as_view()),
    path('check-qr-list-create/', views.CheckQrListCreateViews.as_view()),
    path('filter_check-detail/<int:user_id>/', views.check_and_check_qr_detail_view),
    path('filter_check-list/', views.check_and_check_qr_list_view),
    path('question_answer_list/', views.QuestionAnswerListView.as_view()),
    path('favorites_create/', views.FeaturedUserActionCreateView.as_view()),
    path('favorites_delete/<int:pk>/', views.FeaturedUserActionDeleteView.as_view()),
    path('favorites_list/', views.FeaturedUserActionListView.as_view()),
    path('country-list/', views.CountryListView.as_view()),
]
