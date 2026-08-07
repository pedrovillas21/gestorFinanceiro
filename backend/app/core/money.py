from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


MONEY_QUANTUM = Decimal("0.01")
MAX_MONEY = Decimal("9999999999.99")


def decimal_from_value(value: object) -> Decimal:
    """Converte sem passar por float e entende os formatos 1234.56 e 1.234,56."""
    if isinstance(value, Decimal):
        return value
    text = str(value).strip().replace("R$", "").replace(" ", "")
    if not text:
        raise ValueError("valor vazio")
    if "," in text:
        if "." in text:
            text = text.replace(".", "")
        text = text.replace(",", ".")
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"valor decimal inválido: {value}") from exc


def quantize_money(value: object) -> Decimal:
    result = decimal_from_value(value).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
    if abs(result) > MAX_MONEY:
        raise ValueError("valor excede o limite monetário suportado")
    return result
