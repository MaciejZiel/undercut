import unicodedata


def make_search_name(*parts: str) -> str:
    """Lowercase, diacritics-free form used for searching ("Pérez" -> "perez")."""
    joined = " ".join(p.strip() for p in parts if p and p.strip())
    # Letters such as the Polish "l with stroke" have no decomposition; map them explicitly.
    joined = joined.translate(str.maketrans({"ł": "l", "Ł": "L", "ø": "o", "Ø": "O", "đ": "d"}))
    decomposed = unicodedata.normalize("NFKD", joined)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(stripped.casefold().split())
