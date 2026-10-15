from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .. import services


class UnsubscribeResultSerializer(serializers.Serializer):
    race_result_email = serializers.BooleanField()


class UnsubscribeView(APIView):
    """One-click unsubscribe from the link in e-mails: no login, the token is the credential.

    Both verbs unsubscribe (idempotent): GET serves the plain link in the mail, POST serves RFC 8058
    one-click clients. No session is used, so CSRF does not apply. Opting out is the safe direction,
    so a link prefetcher triggering it is harmless.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        responses=UnsubscribeResultSerializer, operation_id="notifications_unsubscribe_get"
    )
    def get(self, request, token: str):
        return self._unsubscribe(token)

    @extend_schema(
        request=None,
        responses=UnsubscribeResultSerializer,
        operation_id="notifications_unsubscribe_post",
    )
    def post(self, request, token: str):
        return self._unsubscribe(token)

    def _unsubscribe(self, token: str):
        pref = services.unsubscribe(token)
        if pref is None:
            raise NotFound("Unknown unsubscribe link.")
        return Response({"race_result_email": pref.race_result_email})
