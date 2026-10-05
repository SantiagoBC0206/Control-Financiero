"""
utilidades.py — Funciones pequeñas que se usan en varias pantallas.
"""


def pesos(valor):
    """Formatea pesos colombianos: 1234567 -> $1.234.567 y -5000 -> -$5.000."""
    signo = "-" if valor < 0 else ""
    return f"{signo}${abs(valor):,.0f}".replace(",", ".")
