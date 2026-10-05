"""
migrar_datos_viejos.py — Se ejecuta UNA vez (o las veces que quieras, es seguro).

Crea las tablas nuevas dentro de transporte.db y copia allí los días que ya
tenías en la tabla vieja 'registros'. La tabla vieja NO se borra.

Uso (desde la carpeta del proyecto):
    python migrar_datos_viejos.py
"""

import db

# Crear las tablas nuevas (si ya existen, no pasa nada)
db.init_db()

# Copiar los registros de la tabla vieja
migrados, omitidos = db.migrar_registros_antiguos()
print(f"Días migrados: {migrados}")
print(f"Días omitidos (ya existían en el sistema nuevo): {omitidos}")

# Mostrar un resumen para comprobar que los totales cuadran
resumen = db.resumen_dias()
if resumen.empty:
    print("No hay días en el sistema nuevo todavía.")
else:
    print(f"Total de días en el sistema nuevo: {len(resumen)}")
    print(f"Total ingresos: ${resumen['Total Ingresos'].sum():,.0f}")
    print(f"Total gastos:   ${resumen['Total Gastos'].sum():,.0f}")
    print(f"Ganancia:       ${resumen['Ganancia Est'].sum():,.0f}")
