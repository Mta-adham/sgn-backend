"""Member industries.

A member can operate across several industries, so these are stored as an array rather
than a single value. This module is the single source of truth for what is valid and is
served to the frontend at GET /api/members/industries.

Each entry carries:
  name         canonical label, and what is stored on the member record
  group        sector grouping, used to organise the picker UI
  vision_2030  True for sectors named in a Saudi Vision 2030 programme or target

The vision_2030 flag marks sectors tied to a specific Vision 2030 programme, giga-project
or localisation target (NIDLP, Financial Sector Development, Health Sector Transformation,
Quality of Life, Human Capability Development, the National Biotechnology Strategy, the
Saudi Green Initiative and the giga-projects). It is deliberately not "anything
economically useful" - almost every industry touches the Vision somewhere, and a flag that
marks everything marks nothing.
"""

INDUSTRY_DEFINITIONS: list[dict] = [
    # --- Energy, resources and sustainability -------------------------------------
    {"name": "Oil & Gas", "group": "Energy & Resources", "vision_2030": False},
    {"name": "Petrochemicals & Chemicals", "group": "Energy & Resources", "vision_2030": False},
    {"name": "Renewable Energy", "group": "Energy & Resources", "vision_2030": True},
    {"name": "Hydrogen & Clean Fuels", "group": "Energy & Resources", "vision_2030": True},
    {"name": "Nuclear Energy", "group": "Energy & Resources", "vision_2030": False},
    {"name": "Mining & Metals", "group": "Energy & Resources", "vision_2030": True},
    {"name": "Water & Desalination", "group": "Energy & Resources", "vision_2030": True},
    {"name": "Environment & Sustainability", "group": "Energy & Resources", "vision_2030": False},
    {"name": "Waste & Circular Economy", "group": "Energy & Resources", "vision_2030": False},

    # --- Technology ---------------------------------------------------------------
    {"name": "Technology & Software", "group": "Technology & Digital", "vision_2030": True},
    {"name": "Artificial Intelligence & Data", "group": "Technology & Digital", "vision_2030": True},
    {"name": "Cybersecurity", "group": "Technology & Digital", "vision_2030": False},
    {"name": "Telecommunications", "group": "Technology & Digital", "vision_2030": False},
    {"name": "Gaming & Esports", "group": "Technology & Digital", "vision_2030": True},
    {"name": "Space & Satellite", "group": "Technology & Digital", "vision_2030": True},
    {"name": "Semiconductors & Hardware", "group": "Technology & Digital", "vision_2030": False},

    # --- Financial services -------------------------------------------------------
    {"name": "Banking & Financial Services", "group": "Financial Services", "vision_2030": True},
    {"name": "Islamic Finance", "group": "Financial Services", "vision_2030": False},
    {"name": "Fintech", "group": "Financial Services", "vision_2030": True},
    {"name": "Investment & Asset Management", "group": "Financial Services", "vision_2030": False},
    {"name": "Venture Capital & Private Equity", "group": "Financial Services", "vision_2030": False},
    {"name": "Insurance", "group": "Financial Services", "vision_2030": False},

    # --- Built environment and mobility -------------------------------------------
    {"name": "Real Estate & Development", "group": "Infrastructure & Mobility", "vision_2030": True},
    {"name": "Giga-projects & Smart Cities", "group": "Infrastructure & Mobility", "vision_2030": True},
    {"name": "Construction & Engineering", "group": "Infrastructure & Mobility", "vision_2030": False},
    {"name": "Architecture & Design", "group": "Infrastructure & Mobility", "vision_2030": False},
    {"name": "Logistics & Supply Chain", "group": "Infrastructure & Mobility", "vision_2030": True},
    {"name": "Transport & Mobility", "group": "Infrastructure & Mobility", "vision_2030": False},
    {"name": "Maritime & Ports", "group": "Infrastructure & Mobility", "vision_2030": False},
    {"name": "Aviation & Aerospace", "group": "Infrastructure & Mobility", "vision_2030": True},
    {"name": "Rail", "group": "Infrastructure & Mobility", "vision_2030": False},
    {"name": "Automotive & EV", "group": "Infrastructure & Mobility", "vision_2030": True},

    # --- Health and life sciences -------------------------------------------------
    {"name": "Healthcare Services", "group": "Health & Life Sciences", "vision_2030": True},
    {"name": "Pharmaceuticals", "group": "Health & Life Sciences", "vision_2030": False},
    {"name": "Biotechnology", "group": "Health & Life Sciences", "vision_2030": True},
    {"name": "Medical Devices", "group": "Health & Life Sciences", "vision_2030": False},
    {"name": "Digital Health", "group": "Health & Life Sciences", "vision_2030": False},

    # --- Tourism, culture and lifestyle -------------------------------------------
    {"name": "Tourism & Hospitality", "group": "Tourism, Culture & Lifestyle", "vision_2030": True},
    {"name": "Entertainment & Leisure", "group": "Tourism, Culture & Lifestyle", "vision_2030": True},
    {"name": "Events & Experiences", "group": "Tourism, Culture & Lifestyle", "vision_2030": False},
    {"name": "Culture & Heritage", "group": "Tourism, Culture & Lifestyle", "vision_2030": True},
    {"name": "Arts & Creative Industries", "group": "Tourism, Culture & Lifestyle", "vision_2030": False},
    {"name": "Film, TV & Media", "group": "Tourism, Culture & Lifestyle", "vision_2030": True},
    {"name": "Music", "group": "Tourism, Culture & Lifestyle", "vision_2030": False},
    {"name": "Fashion & Luxury", "group": "Tourism, Culture & Lifestyle", "vision_2030": False},
    {"name": "Sports", "group": "Tourism, Culture & Lifestyle", "vision_2030": True},
    {"name": "Food & Beverage", "group": "Tourism, Culture & Lifestyle", "vision_2030": False},

    # --- Industry, manufacturing and consumer -------------------------------------
    {"name": "Manufacturing & Industrial", "group": "Industry & Consumer", "vision_2030": True},
    {"name": "Defence & Security", "group": "Industry & Consumer", "vision_2030": True},
    {"name": "Agriculture & Food Security", "group": "Industry & Consumer", "vision_2030": True},
    {"name": "Retail & E-commerce", "group": "Industry & Consumer", "vision_2030": False},
    {"name": "Consumer Goods", "group": "Industry & Consumer", "vision_2030": False},

    # --- Public sector, education and professional services -----------------------
    {"name": "Government & Public Sector", "group": "Public & Professional", "vision_2030": False},
    {"name": "Education & Training", "group": "Public & Professional", "vision_2030": True},
    {"name": "Research & Academia", "group": "Public & Professional", "vision_2030": False},
    {"name": "Legal Services", "group": "Public & Professional", "vision_2030": False},
    {"name": "Consulting & Professional Services", "group": "Public & Professional", "vision_2030": False},
    {"name": "Human Resources & Talent", "group": "Public & Professional", "vision_2030": False},
    {"name": "Marketing & Communications", "group": "Public & Professional", "vision_2030": False},
    {"name": "Non-profit & Social Impact", "group": "Public & Professional", "vision_2030": True},
    {"name": "Other", "group": "Public & Professional", "vision_2030": False},
]

# Flat canonical list, in definition order.
INDUSTRIES: list[str] = [entry["name"] for entry in INDUSTRY_DEFINITIONS]

VISION_2030_INDUSTRIES: list[str] = [
    entry["name"] for entry in INDUSTRY_DEFINITIONS if entry["vision_2030"]
]

INDUSTRY_GROUPS: list[str] = list(dict.fromkeys(e["group"] for e in INDUSTRY_DEFINITIONS))

# Labels from the previous short list, mapped onto the new set so existing member records
# and any client still sending the old vocabulary keep their meaning.
LEGACY_INDUSTRY_ALIASES: dict[str, str] = {
    "technology": "Technology & Software",
    "finance & banking": "Banking & Financial Services",
    "energy & oil": "Oil & Gas",
    "healthcare": "Healthcare Services",
    "construction & real estate": "Construction & Engineering",
    "education": "Education & Training",
    "manufacturing": "Manufacturing & Industrial",
    "retail & e commerce": "Retail & E-commerce",
    "consulting": "Consulting & Professional Services",
}


def normalise_industries(values: list[str] | None) -> list[str]:
    """Keep only recognised industries, de-duplicated and in canonical order.

    Labels from the previous vocabulary are translated rather than dropped.
    """
    if not values:
        return []

    lookup = {name.lower(): name for name in INDUSTRIES}
    seen: set[str] = set()
    for raw in values:
        key = raw.strip().lower()
        if key in lookup:
            seen.add(lookup[key])
        elif key in LEGACY_INDUSTRY_ALIASES:
            seen.add(LEGACY_INDUSTRY_ALIASES[key])

    return [name for name in INDUSTRIES if name in seen]
