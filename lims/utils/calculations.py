from decimal import Decimal, ROUND_HALF_UP


def calculate_cho_and_me(moisture, protein, fat, fiber, ash):
    try:
        cho = round(100 - (moisture + protein + fat + fiber + ash), 2)
        me = round((4 * protein) + (9 * fat) + (4 * cho), 2)
        return cho, me
    except:
        return None, None


def calculate_nfe_and_me(results: dict) -> tuple:
    """
    Accepts a dictionary like:
    {
        "Protein": 20.1,
        "Fat": 5.2,
        "Ash": 1.7,
        "Moisture": 10.3,
        "Fiber": 2.1
    }
    Returns (Carbohydrate (NFE), ME) or (None, None)
    """
    try:
        protein = Decimal(results.get("Protein", 0))
        fat = Decimal(results.get("Fat", 0))
        ash = Decimal(results.get("Ash", 0))
        moisture = Decimal(results.get("Moisture", 0))
        fiber = Decimal(results.get("Fiber", 0))

        nfe = Decimal("100") - (protein + fat + ash + moisture + fiber)
        me = (protein * 4) + (fat * 9) + (nfe * 4)

        nfe = nfe.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        me = me.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return float(nfe), float(me)
    except Exception as e:
        print("[calculate_nfe_and_me] Error:", e)
        return None, None
