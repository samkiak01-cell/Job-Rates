import requests

FRANKFURTER_BASE = "https://api.frankfurter.app/latest"


def convert_currency(
    amount: float,
    from_code: str,
    to_code: str,
    api_key: str = "",  # unused — frankfurter.app requires no API key
) -> float | None:
    """Convert amount from one currency to another using frankfurter.app (ECB rates, no key needed)."""

    if from_code == to_code:
        return amount

    if amount is None or amount == 0:
        return None

    params = {
        "from": from_code.upper(),
        "to": to_code.upper(),
        "amount": amount,
    }

    try:
        resp = requests.get(FRANKFURTER_BASE, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        rates = data.get("rates", {})
        result = rates.get(to_code.upper())
        if result is not None:
            return float(result)

        print(f"[currency] Conversion failed for {from_code}->{to_code}: {data}")
        return None

    except requests.exceptions.HTTPError as e:
        print(f"[currency] HTTP error for {from_code}->{to_code}: {e}")
        return None
    except Exception as e:
        print(f"[currency] Error for {from_code}->{to_code}: {e}")
        return None
