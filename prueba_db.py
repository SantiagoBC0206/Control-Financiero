"""
prueba_db.py — Comprueba que db.py funciona, usando una base TEMPORAL.
No toca tu transporte.db real.

Uso:
    python prueba_db.py
"""

import os
import sqlite3
import tempfile

import db

# Base temporal (se borra sola al terminar)
carpeta = tempfile.mkdtemp()
db.RUTA_DB = os.path.join(carpeta, "prueba.db")

# 1) Simular la tabla vieja 'registros' con dos días
conn = sqlite3.connect(db.RUTA_DB)
conn.execute("""
    CREATE TABLE registros (
        fecha TEXT PRIMARY KEY, didi REAL, indrive REAL, uber REAL, extras REAL,
        gasolina REAL, apps REAL, comida REAL, otros_gastos REAL,
        efectivo REAL, nequi REAL
    )
""")
conn.execute("INSERT INTO registros VALUES ('2025-08-01',0,42439,33093,12000,60000,17000,0,0,16000,98400)")
conn.execute("INSERT INTO registros VALUES ('2025-08-06',55962,37500,0,63000,60000,0,0,235000,61000,62600)")
conn.commit()
conn.close()

# 2) Crear tablas nuevas y migrar
db.init_db()
assert db.migrar_registros_antiguos() == (2, 0), "debían migrarse 2 días"
assert db.migrar_registros_antiguos() == (0, 2), "la segunda vez no debe duplicar"

# 3) Los números deben coincidir con el Excel de Agosto 2025
r = db.resumen_dias().set_index("Fecha")
assert r.loc["2025-08-01", "Total Ingresos"] == 87532
assert r.loc["2025-08-01", "Total Gastos"] == 77000
assert r.loc["2025-08-01", "Ganancia Est"] == 10532
assert r.loc["2025-08-01", "Total Disp"] == 114400
assert r.loc["2025-08-01", "Diferencia"] == -103868
assert r.loc["2025-08-06", "Ganancia Est"] == -138538
assert r.loc["2025-08-06", "Diferencia"] == -262138

# 4) Editar un día reemplaza, no duplica
db.guardar_dia("2025-08-01", {"InDrive": 50000}, {"Gasolina": 60000}, {"Nequi": 1000})
assert len(db.resumen_dias()) == 2
assert db.cargar_dia("2025-08-01")["ingresos"] == {"InDrive": 50000}

# 5) Un día solo con gasto (como el 31 de agosto) y una plataforma nueva
db.guardar_dia("2025-08-31", {}, {"Otros Gastos": 200000}, {})
db.guardar_dia("2025-09-01", {"Cabify": 70000, "Uber": 20000}, {}, {"Efectivo": 90000})
r = db.resumen_dias().set_index("Fecha")
assert r.loc["2025-08-31", "Ganancia Est"] == -200000
assert r.loc["2025-09-01", "Cabify"] == 70000
assert "Cabify" in db.nombres_disponibles("ingresos")

# 6) Filtro por rango de fechas
assert len(db.resumen_dias(desde="2025-09-01")) == 1

# 7) Borrar un día
db.eliminar_dia("2025-09-01")
assert db.cargar_dia("2025-09-01") is None

print("✅ Todas las pruebas pasaron")
