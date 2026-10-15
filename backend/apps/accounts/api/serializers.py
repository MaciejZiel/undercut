from rest_framework import serializers

from apps.accounts.models import User
from apps.accounts.services import MAX_FAVORITE_CONSTRUCTORS, MAX_FAVORITE_DRIVERS
from apps.notifications.services import race_result_email_enabled


class UserSerializer(serializers.ModelSerializer):
    can_predict = serializers.BooleanField(read_only=True)
    race_result_email = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "display_name",
            "email",
            "email_verified",
            "can_predict",
            "timezone",
            "theme",
            "is_demo",
            "race_result_email",
        ]
        read_only_fields = fields

    def get_race_result_email(self, user) -> bool:
        return race_result_email_enabled(user)


class MeSerializer(serializers.Serializer):
    is_authenticated = serializers.BooleanField()
    user = UserSerializer(allow_null=True)


class CsrfSerializer(serializers.Serializer):
    csrf_token = serializers.CharField()


class SettingsUpdateSerializer(serializers.Serializer):
    display_name = serializers.CharField(required=False)
    timezone = serializers.CharField(required=False)
    theme = serializers.ChoiceField(choices=["system", "light", "dark"], required=False)
    race_result_email = serializers.BooleanField(required=False)


class DeleteAccountSerializer(serializers.Serializer):
    display_name = serializers.CharField(help_text="The account's display name, typed to confirm.")


class FavoriteDriverSerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.SerializerMethodField()
    code = serializers.CharField(allow_null=True)

    def get_name(self, driver) -> str:
        return f"{driver.given_name} {driver.family_name}"

    def to_representation(self, driver):
        data = super().to_representation(driver)
        data["code"] = driver.code or None
        return data


class FavoriteConstructorSerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()


class FavoriteLimitsSerializer(serializers.Serializer):
    drivers = serializers.IntegerField(default=MAX_FAVORITE_DRIVERS)
    constructors = serializers.IntegerField(default=MAX_FAVORITE_CONSTRUCTORS)


class FavoritesSerializer(serializers.Serializer):
    drivers = FavoriteDriverSerializer(many=True)
    constructors = FavoriteConstructorSerializer(many=True)
    limits = FavoriteLimitsSerializer()


class FavoriteStateSerializer(serializers.Serializer):
    favorite = serializers.BooleanField()


class ErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()
    code = serializers.CharField()
