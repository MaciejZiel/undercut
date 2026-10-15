import time

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.http import JsonResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from . import status

# The migration plan reads every migration file; once it is clean it stays clean until a deploy,
# which restarts the process. Re-check a positive result at most once a minute.
_MIGRATIONS_TTL = 60.0
_migrations_ok_until = 0.0


def _database_ok() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return False
    return True


def _migrations_ok() -> bool:
    global _migrations_ok_until
    if time.monotonic() < _migrations_ok_until:
        return True
    try:
        executor = MigrationExecutor(connection)
        pending = executor.migration_plan(executor.loader.graph.leaf_nodes())
    except Exception:
        return False
    if pending:
        return False
    _migrations_ok_until = time.monotonic() + _MIGRATIONS_TTL
    return True


def _outbox_ok() -> bool:
    try:
        return not status.outbox_problems()
    except Exception:
        return False


def ready(_request):
    """Readiness: database reachable, migrations applied, outbox draining.

    Public, so it only reports pass/fail per check and never counts or names.
    """
    checks = {"database": _database_ok()}
    if checks["database"]:
        checks["migrations"] = _migrations_ok()
        checks["outbox"] = _outbox_ok()
    else:
        checks["migrations"] = checks["outbox"] = False
    ok = all(checks.values())
    return JsonResponse(
        {"status": "ready" if ok else "not_ready", "checks": checks}, status=200 if ok else 503
    )


class OpsStatusView(APIView):
    """Operational summary for staff: outbox, sync jobs, heartbeats, data freshness, sizes."""

    permission_classes = [IsAdminUser]
    throttle_classes: list = []

    @extend_schema(responses=OpenApiTypes.OBJECT, tags=["ops"])
    def get(self, request):
        return Response(status.full_status())
