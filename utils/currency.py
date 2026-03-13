import requests

EXCHANGERATE_BASE = "https://api.exchangerate.host/convert"


def convert_currency(
    amount: float,
    from_code: str,
    to_code: str,
    api_key: str,
) -> float | None:
    """Convert amount from one currency to another using exchangerate.host."""

    if from_code == to_code:
        return amount

    if amount is None or amount == 0:
        return None

    params = {
        "from": from_code.upper(),
        "to": to_code.upper(),
        "amount": amount,
        "access_key": api_key,
    }

    try:
        resp = requests.get(EXCHANGERATE_BASE, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("success") and data.get("result") is not None:
            return float(data["result"])

        # Some versions return 'result' directly without 'success' flag
        result = data.get("result")
        if result is not None:
            return float(result)

        print(f"[currency] Conversion failed for {from_code}->{to_code}: {data}")
        return None

    except requests.exceptions.HTTPError as e:
        if e.response and e.response.status_code == 429:
            print(f"[currency] Rate limited (429) for {from_code}->{to_code}")
        else:
            print(f"[currency] HTTP error for {from_code}->{to_code}: {e}")
        return None
    except Exception as e:
        print(f"[currency] Error for {from_code}->{to_code}: {e}")
        return None
