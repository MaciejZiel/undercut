from allauth.account.adapter import DefaultAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        # Set the display name before the first INSERT so the unique constraint protects it.
        user.display_name = form.cleaned_data.get("display_name")
        return super().save_user(request, user, form, commit=commit)
