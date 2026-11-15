"""The `<fk>_id: int` annotations on models (for pyright) must match the field's nullability."""

import typing

from django.apps import apps


def _annotated_ids():
    for model in apps.get_models():
        if not model.__module__.startswith("apps."):
            continue
        for klass in model.__mro__:
            for name, hint in vars(klass).get("__annotations__", {}).items():
                if name.endswith("_id"):
                    yield model, name, hint


def _optional(hint) -> bool:
    # A string under `from __future__ import annotations`, a real type otherwise.
    if isinstance(hint, str):
        return "None" in [part.strip() for part in hint.split("|")]
    return type(None) in typing.get_args(hint)


def test_every_annotated_id_is_a_foreign_key_with_matching_nullability():
    checked = 0
    for model, name, hint in _annotated_ids():
        field = model._meta.get_field(name.removesuffix("_id"))
        assert field.is_relation, f"{model.__name__}.{name}"
        assert field.attname == name, f"{model.__name__}.{name}"
        optional = _optional(hint)
        assert optional == field.null, f"{model.__name__}.{name}: null={field.null}, hint {hint}"
        checked += 1
    assert checked > 20
