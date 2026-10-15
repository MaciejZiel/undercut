from django import forms
from django.contrib.auth import get_user_model

from .validators import validate_display_name


class SignupExtraFieldsForm(forms.Form):
    """Extra registration field wired into allauth through ACCOUNT_SIGNUP_FORM_CLASS."""

    display_name = forms.CharField(max_length=60)

    def clean_display_name(self) -> str:
        value = validate_display_name(self.cleaned_data["display_name"])
        if get_user_model().objects.filter(display_name__iexact=value).exists():
            raise forms.ValidationError("This display name is already taken.", code="taken")
        return value

    def signup(self, request, user) -> None:
        """Required by allauth. The name is stored in AccountAdapter.save_user (same INSERT)."""
