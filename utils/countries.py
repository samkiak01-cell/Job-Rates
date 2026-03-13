import pycountry
import geonamescache

_gc = None

def _get_gc():
    global _gc
    if _gc is None:
        _gc = geonamescache.GeonamesCache()
    return _gc


def _alpha2(country_name: str) -> str | None:
    """Return ISO alpha-2 code for a country name, or None."""
    pc = pycountry.countries.get(name=country_name)
    if pc:
        return pc.alpha_2
    try:
        results = pycountry.countries.search_fuzzy(country_name)
        return results[0].alpha_2 if results else None
    except Exception:
        return None

CURRENCY_MAP = {
    "United States": "USD",
    "United Kingdom": "GBP",
    "Canada": "CAD",
    "Australia": "AUD",
    "Germany": "EUR",
    "France": "EUR",
    "Italy": "EUR",
    "Spain": "EUR",
    "Netherlands": "EUR",
    "Belgium": "EUR",
    "Austria": "EUR",
    "Portugal": "EUR",
    "Greece": "EUR",
    "Ireland": "EUR",
    "Finland": "EUR",
    "Japan": "JPY",
    "China": "CNY",
    "India": "INR",
    "Brazil": "BRL",
    "Mexico": "MXN",
    "South Korea": "KRW",
    "Singapore": "SGD",
    "Hong Kong": "HKD",
    "Switzerland": "CHF",
    "Sweden": "SEK",
    "Norway": "NOK",
    "Denmark": "DKK",
    "New Zealand": "NZD",
    "South Africa": "ZAR",
    "Russia": "RUB",
    "Poland": "PLN",
    "Czech Republic": "CZK",
    "Hungary": "HUF",
    "Romania": "RON",
    "Turkey": "TRY",
    "United Arab Emirates": "AED",
    "Saudi Arabia": "SAR",
    "Israel": "ILS",
    "Argentina": "ARS",
    "Chile": "CLP",
    "Colombia": "COP",
    "Peru": "PEN",
    "Malaysia": "MYR",
    "Indonesia": "IDR",
    "Thailand": "THB",
    "Philippines": "PHP",
    "Vietnam": "VND",
    "Pakistan": "PKR",
    "Bangladesh": "BDT",
    "Nigeria": "NGN",
    "Kenya": "KES",
    "Ghana": "GHS",
    "Egypt": "EGP",
}

CURATED_CURRENCIES = ["USD", "EUR", "GBP", "CAD", "AUD"]


def get_all_countries() -> list[str]:
    """Return sorted list of all country names from pycountry."""
    countries = [c.name for c in pycountry.countries]
    return sorted(countries)


def get_country_currency(country_name: str) -> str | None:
    """Return the ISO 4217 currency code for a given country name."""
    # Check direct mapping first
    if country_name in CURRENCY_MAP:
        return CURRENCY_MAP[country_name]

    # Try pycountry lookup (limited — pycountry doesn't have currency data)
    # Fall back to None if unknown
    return None


def get_display_currencies(country_name: str) -> list[str]:
    """Return display currency options with country's native currency prepended if not already in list."""
    native = get_country_currency(country_name)
    currencies = list(CURATED_CURRENCIES)
    if native and native not in currencies:
        currencies = [native] + currencies
    return currencies


def get_regions(country_name: str) -> list[str]:
    """Return sorted top-level subdivision names (states/provinces) for a country."""
    a2 = _alpha2(country_name)
    if not a2:
        return []
    try:
        subs = pycountry.subdivisions.get(country_code=a2)
        if not subs:
            return []
        # Keep only top-level subdivisions (no parent)
        top = [s for s in subs if s.parent_code is None] or list(subs)
        return sorted(set(s.name for s in top))
    except Exception:
        return []


def get_cities(country_name: str, region_name: str = "") -> list[str]:
    """Return sorted city names for a country, optionally filtered by region."""
    a2 = _alpha2(country_name)
    if not a2:
        return []
    try:
        gc = _get_gc()
        cities = [c for c in gc.get_cities().values() if c["countrycode"] == a2]

        if region_name:
            # Find the geonames admin1code that matches the region name
            subs = pycountry.subdivisions.get(country_code=a2) or []
            admin1 = None
            for s in subs:
                if s.name == region_name:
                    admin1 = s.code.split("-")[-1]
                    break
            if admin1:
                cities = [c for c in cities if c.get("admin1code") == admin1]

        # Sort by population desc, cap at 300 to keep the list manageable
        cities.sort(key=lambda c: c.get("population", 0), reverse=True)
        return sorted(set(c["name"] for c in cities[:300]))
    except Exception:
        return []
