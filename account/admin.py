from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.core.exceptions import ValidationError
from .models import MyUser, Country, City, Agreement, Cashback, EmailActive


class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = MyUser
        fields = ('email',)

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Пароли не совпадают")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = MyUser
        fields = ('email', 'password', 'is_active', 'is_admin')


class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = ('id', 'email', 'username', 'level', 'is_active', 'is_verified', 'is_admin')
    list_filter = ('is_admin', 'is_verified')
    fieldsets = (
        (None, {'fields': (
            'username',
            'email',
            'password',
            'phone_number',
            'date_of_birth',
            'country',
            'city',
            'level',
            'balance',
            'price_limit',
            'today_amount',
            'invitation_code',
            'currency',
            'card_number',
            'image',
            'featured_actions',
            'buying_action'
        )}),
        ('Permissions', {'fields': ('is_admin', 'is_active', 'is_verified')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'country', 'city', 'date_of_birth', 'password1', 'password2'),
        }),
    )
    search_fields = ('email', 'country')
    ordering = ('email', 'balance')
    filter_horizontal = ()


admin.site.register(EmailActive)
admin.site.register(Cashback)
admin.site.register(Agreement)
admin.site.register(MyUser, UserAdmin)
admin.site.register(Country)
admin.site.register(City)
