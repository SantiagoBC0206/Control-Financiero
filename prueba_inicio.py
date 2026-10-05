"""
prueba_inicio.py — Prueba la pantalla de Inicio con datos inventados (base temporal).

Uso:  python prueba_inicio.py
"""

import os
import tempfile
from datetime import timedelta

from streamlit.testing.v1 import AppTest

import db
from utilidades import hoy, pesos

db.RUTA_DB = os.path.join(tempfile.mkdtemp(), "prueba.db")
os.environ["RUTA_DB"] = db.RUTA_DB
db.init_db()

h = hoy()
# Anteayer: 100.000 de ingresos, 60.000 de gasolina -> ganancia 40.000
db.guardar_dia(h - timedelta(days=2), {"Uber": 100000}, {"Gasolina": 60000}, {"Efectivo": 40000})
# Ayer: día de descanso (no cuenta como trabajado)
db.guardar_dia(h - timedelta(days=1), {}, {}, {})
# Hoy: Didi 150.000 + InDrive 50.000, gasolina 60.000 -> ganancia 140.000
db.guardar_dia(h, {"Didi": 150000, "InDrive": 50000}, {"Gasolina": 60000}, {"Nequi": 140000})

at = AppTest.from_file("app.py", default_timeout=30)
at.secrets["password"] = "clave_de_prueba"
at.run()
at.text_input[0].set_value("clave_de_prueba")
at.button[0].click().run()
assert not at.exception, at.exception

metricas = {m.label: m.value for m in at.metric}
deltas = {m.label: m.delta for m in at.metric}

# HOY (comparado con el último día TRABAJADO, no con el día de descanso de ayer)
assert metricas["💰 Ganancia de hoy"] == pesos(140000)
assert deltas["💰 Ganancia de hoy"] == "+" + pesos(100000)

# MES / AÑO (si hoy es día 1 o 2 del mes, los días anteriores caen en otro mes; no se verifica)
if (h - timedelta(days=2)).month == h.month:
    assert metricas["🏆 Ganancia neta del mes"] == pesos(180000)
    assert metricas["🚗 Días trabajados"] == "2"
    assert metricas["📊 Promedio por día trabajado"] == pesos(90000)
    assert metricas["🏆 Ganancia neta del año"] == pesos(180000)

print("✅ El Inicio calcula bien el día, el mes y el año")
