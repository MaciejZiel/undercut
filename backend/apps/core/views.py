from django.db import connection
from django.http import JsonResponse


def health(_request):
    """Liveness/readiness probe: verifies the database answers."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return JsonResponse({"status": "ok"})
