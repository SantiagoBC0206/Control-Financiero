"""
prueba_importador.py — Prueba el importador con archivos inventados (base temporal).

Uso:  python prueba_importador.py
"""

import io
import os
import tempfile

import pandas as pd
from streamlit.testing.v1 import AppTest

import db
import importador as imp

db.RUTA_DB = os.path.join(tempfile.mkdtemp(), "prueba.db")
os.environ["RUTA_DB"] = db.RUTA_DB
db.init_db()

# --- Un CSV con el mismo formato de tu Excel (con fila "Total Mes" y un día de descanso)
CSV = (
    "Fecha,Didi,InDrive,Uber,Extras,Total Ingresos,Gasolina,Apps,Comida,Otros Gastos,"
    "Total Gastos,Ganancia Est,Efectivo,Nequi,Total Disp,Diferencia\n"
    "2025-08-01,,42439,33093,12000,87532,60000,17000,,,77000,10532,16000,98400,114400,-103868\n"
    "2025-08-02,,,,,0,,,,,0,0,,,0,0\n"
    "2025-08-06,55962,37500,,63000,156462,60000,,,235000,295000,-138538,61000,62600,123600,-262138\n"
    "Total Mes,,,,,243994,,,,,372000,-128006,,,238000,-366006\n"
)

# 1) Leer y analizar
hojas = imp.leer_archivo("agosto.csv", CSV.encode("utf-8"))
assert len(hojas) == 1
a = imp.analizar_hoja(hojas[0][1])
assert len(a["dias"]) == 2 and a["sin_movimiento"] == 1, "debía haber 2 días y 1 de descanso"
assert all(c == e for _, c, e in a["comparacion"]), a["comparacion"]   # totales cuadran con el Excel
assert not a["descartadas"] and not a["avisos"], (a["descartadas"], a["avisos"])

# 2) Primera importación: todo nuevo
imp.clasificar(a["dias"])
assert [d["estado"] for d in a["dias"]] == ["nuevo", "nuevo"]
assert imp.importar(a["dias"]) == (2, 0, 0)
r = db.resumen_dias().set_index("Fecha")
assert r.loc["2025-08-01", "Total Disp"] == 114400 and r.loc["2025-08-06", "Ganancia Est"] == -138538

# 3) Subir lo mismo otra vez: no duplica nada
a2 = imp.analizar_hoja(hojas[0][1])
imp.clasificar(a2["dias"])
assert [d["estado"] for d in a2["dias"]] == ["igual", "igual"]
assert imp.importar(a2["dias"]) == (0, 0, 2)
assert len(db.resumen_dias()) == 2

# 4) Un día cambia en el sistema: se detecta como 'distinto' y respeta la decisión
db.guardar_dia("2025-08-01", {"Uber": 1000}, {}, {})
a3 = imp.analizar_hoja(hojas[0][1])
imp.clasificar(a3["dias"])
assert [d["estado"] for d in a3["dias"]] == ["distinto", "igual"]
assert imp.importar(a3["dias"], reemplazar_distintos=False) == (0, 0, 2)
assert db.cargar_dia("2025-08-01")["ingresos"] == {"Uber": 1000}          # se conservó
assert imp.importar(a3["dias"], reemplazar_distintos=True) == (0, 1, 1)
assert db.cargar_dia("2025-08-01")["ingresos"]["InDrive"] == 42439        # se reemplazó

# 5) Un Excel real (.xlsx): título arriba, varias hojas, fechas reales y valores con "$" y puntos
filas = [
    ["CONTROL MENSUAL", None, None, None, None, None, None],
    [None] * 7,
    ["Fecha", "Didi", "InDrive", "Gasolina", "Efectivo", "Nequi", "Notas"],
    [pd.Timestamp("2025-09-01"), "$120.000", 80000, 60000, 50000, 90000, "lunes"],
    [pd.Timestamp("2025-09-02"), None, None, None, None, None, None],
    ["Promedio", 1, 2, 3, 4, 5, None],           # fila rara: se descarta con aviso
    [pd.Timestamp("2025-09-03"), "abc", 1, 1, 1, 1, None],  # valor que no es número: se descarta
]
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine="openpyxl") as w:
    pd.DataFrame([["solo texto"]]).to_excel(w, sheet_name="Resumen", header=False, index=False)
    pd.DataFrame(filas).to_excel(w, sheet_name="Septiembre", header=False, index=False)
hojas = dict(imp.leer_archivo("sep.xlsx", buffer.getvalue()))
assert imp.analizar_hoja(hojas["Resumen"]) is None            # hoja sin Fecha: se omite
x = imp.analizar_hoja(hojas["Septiembre"])
assert len(x["dias"]) == 1 and x["sin_movimiento"] == 1
assert len(x["descartadas"]) == 2
d = x["dias"][0]
assert d["ingresos"] == {"Didi": 120000, "InDrive": 80000} and d["observaciones"] == "lunes"

# 6) Excel duplicado de agosto (fechas viejas) pero guardado como "Octubre 2025"
assert imp.detectar_mes("Hoja1", "Plantilla_Control_Octubre_2025.xlsx") == (2025, 10)
assert imp.detectar_mes("Agosto 2025", "x.csv") == (2025, 8)
assert imp.detectar_mes("Control_Sep_2025.xlsx") == (2025, 9)
assert imp.detectar_mes("Hoja1", "archivo.xlsx") is None
copia = (
    "Fecha,Didi,Gasolina,Efectivo,Nequi\n"
    "2025-08-01,100000,60000,10000,90000\n"
    "2025-08-15,50000,60000,0,40000\n"
    "2025-08-31,70000,60000,5000,60000\n"      # el día 31 no existe en septiembre
)
crudo = imp.leer_archivo("Control_Septiembre_2025.csv", copia.encode())[0][1]
sin_cambio = imp.analizar_hoja(crudo)
assert sin_cambio["meses_en_fechas"] == {(2025, 8)}                      # delata el desajuste
assert str(sin_cambio["dias"][0]["fecha"]) == "2025-08-01"               # sin corregir: fecha vieja
corregido = imp.analizar_hoja(crudo, mes_forzado=(2025, 9))
assert [str(d["fecha"]) for d in corregido["dias"]] == ["2025-09-01", "2025-09-15"]
assert len(corregido["descartadas"]) == 1 and "31" in corregido["descartadas"][0][1]
octubre = imp.analizar_hoja(crudo, mes_forzado=(2025, 10))
assert [str(d["fecha"]) for d in octubre["dias"]] == ["2025-10-01", "2025-10-15", "2025-10-31"]

# 7) La pantalla de importar abre sin errores
at = AppTest.from_file("app.py", default_timeout=30)
at.secrets["password"] = "clave_de_prueba"
at.run()
at.text_input[0].set_value("clave_de_prueba")
at.button[0].click().run()
at.radio[0].set_value("📥 Importar Excel").run()
assert not at.exception, at.exception
assert at.subheader[0].value == "📥 Importar Excel"

print("✅ El importador funciona: lee, comprueba totales y no duplica")
