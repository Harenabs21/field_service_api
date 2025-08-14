from datetime import datetime


def parse_date(value):
    """
    Retourne une date au format string YYYY-MM-DD.
    Si la valeur est vide ou invalide, retourne la date d'aujourd'hui.
    """
    if not value or (isinstance(value, str) and not value.strip()):
        return datetime.now().strftime("%Y-%m-%d")

    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(str(value).strip(), fmt).strftime(
                "%Y-%m-%d"
                )
        except ValueError:
            continue

    return datetime.now().strftime("%Y-%m-%d")
