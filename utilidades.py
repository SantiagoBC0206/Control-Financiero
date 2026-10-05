"""
utilidades.py — Funciones pequeñas que se usan en varias pantallas.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]
MESES_CORTOS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def pesos(valor):
    """Formatea pesos colombianos: 1234567 -> $1.234.567 y -5000 -> -$5.000."""
    signo = "-" if valor < 0 else ""
    return f"{signo}${abs(valor):,.0f}".replace(",", ".")


def hoy():
    """Fecha de hoy en Colombia.

    Importante: cuando la app esté en internet, el servidor usa la hora UTC y
    después de las 7 p. m. ya sería "mañana". Por eso se fija la zona horaria.
    """
    try:
        return datetime.now(ZoneInfo("America/Bogota")).date()
    except Exception:  # si el computador no tiene datos de zonas horarias
        return date.today()


def nombre_mes(anio_mes):
    """'2025-08' -> 'Agosto 2025'."""
    anio, mes = anio_mes.split("-")
    return f"{MESES[int(mes) - 1]} {anio}"
