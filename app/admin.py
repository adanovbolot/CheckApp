from django.contrib import admin
from .models import *
from account.models import CardNumber


class CheckAdmin(admin.ModelAdmin):
    list_display = ['user', 'status', 'created_date']
    list_filter = ('status', 'created_date')


class CheckQrAdmin(admin.ModelAdmin):
    list_display = ['user', 'status', 'created_date']
    list_filter = ('status', 'created_date')


class SlideAdmin(admin.ModelAdmin):
    list_display = ['cover_image', 'ordering']


class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'has_action']
    search_fields = ['name']


class CurrencyAdmin(admin.ModelAdmin):
    list_display = ['char_code', 'actual_value', 'updated_date', 'is_active']
    list_filter = ('is_active', 'created_date')
    search_fields = ['char_code']


class SupportAdmin(admin.ModelAdmin):
    list_display = ['created_date', 'status']
    list_filter = ('created_date', 'status')
    search_fields = ['description']


class AnswerQuestionAdmin(admin.ModelAdmin):
    list_display = ['question', 'created_date']
    list_filter = ('created_date',)
    search_fields = ['question']


class LevelPriceAdmin(admin.ModelAdmin):
    list_display = ['level', 'price', 'limit', 'created_date', 'is_active']
    list_filter = ('is_active', 'created_date', 'level')


class LevelPaymentAdmin(admin.ModelAdmin):
    list_display = ['user', 'level', 'status', 'created_date']
    list_filter = ('status', 'created_date', 'level')
    search_fields = ['user', 'level']


class ReferralCodeAdmin(admin.ModelAdmin):
    list_display = ['invites', 'invited', 'created_date']
    list_filter = ('created_date', )
    search_fields = ['invites', 'invited']


class PasscodeAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_date']
    list_filter = ('created_date', )


class ActionAdmin(admin.ModelAdmin):
    list_display = ['title', 'start_date', 'end_date', 'is_paid', 'is_active']
    list_filter = ('start_date', 'section', 'end_date', 'is_paid', 'is_active')


class BuyingActionAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'created_date']
    list_filter = ('created_date', )


class WithdrawalRequestsAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_date', 'status']
    list_filter = ['created_date', 'status']
    search_fields = ['user']


class CardNumberAdmin(admin.ModelAdmin):
    list_display = ['user', 'card_number', 'created_date', 'is_active', 'id']
    list_filter = ['created_date', 'is_active', 'id']
    search_fields = ['user', 'id']


class FeaturedUserActionAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'created_date']
    list_filter = ['user', 'action', 'created_date']
    search_fields = ['user']


admin.site.register(PercentageCashbackCheck)
admin.site.register(ReferralCodeBonusInvited)
admin.site.register(ReferralCodeBonus)
admin.site.register(Action, ActionAdmin)
admin.site.register(Currency, CurrencyAdmin)
admin.site.register(Company, CompanyAdmin)
admin.site.register(Check, CheckAdmin)
admin.site.register(CheckQr, CheckQrAdmin)
admin.site.register(Slide, SlideAdmin)
admin.site.register(Support)
admin.site.register(AnswerQuestion, AnswerQuestionAdmin)
admin.site.register(LevelPrice, LevelPriceAdmin)
admin.site.register(LevelPayment, LevelPaymentAdmin)
admin.site.register(Passcode, PasscodeAdmin)
admin.site.register(ReferralCode, ReferralCodeAdmin)
admin.site.register(BuyingAction, BuyingActionAdmin)
admin.site.register(StockCategory)
admin.site.register(QuestionAnswer)
admin.site.register(CardNumber)
admin.site.register(WithdrawalRequests, WithdrawalRequestsAdmin)
admin.site.register(CategoriesSupport)
admin.site.register(FeaturedUserAction, FeaturedUserActionAdmin)
