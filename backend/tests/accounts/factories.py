import factory
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model

PASSWORD = "correct-horse-battery"


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user{n}")
    display_name = factory.Sequence(lambda n: f"Fan {n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    email_verified = True
    password = factory.PostGenerationMethodCall("set_password", PASSWORD)

    @factory.post_generation
    def email_address(self, create, extracted, **kwargs):
        """Mirror the allauth e-mail record, which is the source of truth for verification."""
        if create and self.email:
            EmailAddress.objects.create(
                user=self, email=self.email, primary=True, verified=self.email_verified
            )
        if create:
            self.save()


class UnverifiedUserFactory(UserFactory):
    email_verified = False
