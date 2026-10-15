"""Public id lookups other modules may use instead of importing catalog models."""


def season_ids_by_year() -> dict[int, int]:
    from .models import Season

    return dict(Season.objects.values_list("year", "pk"))


def driver_ids_by_jolpica_id() -> dict[str, int]:
    from .models import Driver

    return dict(Driver.objects.exclude(jolpica_id="").values_list("jolpica_id", "pk"))


def constructor_ids_by_jolpica_id() -> dict[str, int]:
    from .models import Constructor

    return dict(Constructor.objects.exclude(jolpica_id="").values_list("jolpica_id", "pk"))
