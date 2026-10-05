"""
prueba_app.py — Prueba automática de la app (login + registrar un día).
Usa una base temporal; no toca tu transporte.db.

Uso:  python prueba_app.py
"""

import os
import tempfile

from streamlit.testing.v1 import AppTest

import db

db.RUTA_DB = os.path.join(tempfile.mkdtemp(), "prueba.db")
os.environ["RUTA_DB"] = db.RUTA_DB

at = AppTest.from_file("app.py", default_timeout=30)
at.secrets["password"] = "clave_de_prueba"
at.run()

# Contraseña incorrecta
at.text_input[0].set_value("mala")
at.button[0].click().run()
assert any("incorrecta" in e.value for e in at.error), "debía rechazar la clave"

# Contraseña correcta
at.text_input[0].set_value("clave_de_prueba")
at.button[0].click().run()
assert not at.exception, at.exception
assert at.subheader[0].value == "➕ Registrar día"

# Registrar el 1 de agosto de 2025 igual que el Excel
at.date_input[0].set_value(__import__("datetime").date(2025, 8, 1)).run()
valores = {"InDrive": 42439, "Uber": 33093, "Extras": 12000, "Gasolina": 60000,
           "Apps": 17000, "Efectivo": 16000, "Nequi": 98400}
for campo in at.number_input:
    for nombre, v in valores.items():
        if campo.label == nombre:
            campo.set_value(v)
at.button[0].click().run()
assert not at.exception, at.exception

r = db.resumen_dias().iloc[0]
assert r["Total Ingresos"] == 87532 and r["Total Gastos"] == 77000
assert r["Ganancia Est"] == 10532 and r["Diferencia"] == -103868
assert any("$10.532" in m.value for m in at.metric), "no mostró la ganancia"
print("✅ La app funciona: login, registro y balance del día")
