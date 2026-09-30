"""Member categories.

A member can belong to more than one category (an investor who also owns a company, a
student who is also an entrepreneur), so these are stored as an array rather than a single
value. This list is the single source of truth for what is valid.
"""

MEMBER_CATEGORIES: list[str] = [
    "Student",
    "Professional",
    "Investor",
    "Company Owner",
    "Entrepreneur",
]


def normalise_categories(values: list[str] | None) -> list[str]:
    """Keep only recognised categories, de-duplicated and in canonical order."""
    if not values:
        return []
    lookup = {c.lower(): c for c in MEMBER_CATEGORIES}
    seen = {lookup[v.strip().lower()] for v in values if v.strip().lower() in lookup}
    return [c for c in MEMBER_CATEGORIES if c in seen]
