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
# Anteayer: ingresos 100.000, gasolina 60.000 -> ganancia 40.000, pero disponible 50.000
db.guardar_dia(h - timedelta(days=2), {"Uber": 100000}, {"Gasolina": 60000}, {"Efectivo": 50000})
# Ayer: día de descanso (no cuenta como trabajado)
db.guardar_dia(h - timedelta(days=1), {}, {}, {})
# Hoy: ingresos 200.000, gasolina 60.000 -> ganancia 140.000, pero disponible 120.000
db.guardar_dia(h, {"Didi": 150000, "InDrive": 50000}, {"Gasolina": 60000}, {"Nequi": 120000})

at = AppTest.from_file("app.py", default_timeout=30)
at.secrets["password"] = "clave_de_prueba"
at.run()
at.text_input[0].set_value("clave_de_prueba")
at.button[0].click().run()
assert not at.exception, at.exception

# Algunas etiquetas se repiten en Hoy/Mes/Año: se toma la PRIMERA (la de la pestaña Hoy)
metricas, deltas = {}, {}
for m in at.metric:
    metricas.setdefault(m.label, m.value)
    deltas.setdefault(m.label, m.delta)

# HOY: la cifra principal es el DISPONIBLE (no la ganancia estimada)
assert metricas["💵 Disponible de hoy"] == pesos(120000)
assert deltas["💵 Disponible de hoy"] == "+" + pesos(70000)   # vs. último día trabajado (50.000)
assert metricas["📈 Ganancia estimada"] == pesos(140000)

# MES / AÑO (si hoy es día 1 o 2 del mes, los días anteriores caen en otro mes; no se verifica)
if (h - timedelta(days=2)).month == h.month:
    assert metricas["💵 Total disponible del mes"] == pesos(170000)
    assert metricas["🚗 Días trabajados"] == "2"
    assert metricas["📊 Promedio disponible por día trabajado"] == pesos(85000)  # 170.000 / 2
    assert metricas["💵 Total disponible del año"] == pesos(170000)

print("✅ El Inicio calcula bien el día, el mes y el año")
