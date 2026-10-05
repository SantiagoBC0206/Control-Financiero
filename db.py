"""
db.py — Capa de base de datos del Control Financiero (SQLite).

Aquí vive TODO lo que toca la base de datos. Las pantallas (Streamlit) solo
llaman a estas funciones y nunca escriben SQL directamente.

Diseño (una fila por dato, no una fila gigante por día):
    dias_trabajo : un registro por fecha (+ observaciones)
    ingresos     : valor por plataforma y día   (Didi, InDrive, Uber, Extras, ...)
    gastos       : valor por categoría y día    (Gasolina, Apps, Comida, ...)
    movimientos  : valor por método y día       (Efectivo, Nequi, ...)

Para agregar una plataforma o categoría nueva NO hay que cambiar la base de
datos: basta con guardar un valor con ese nombre.
"""

import os
import sqlite3
from contextlib import contextmanager

import pandas as pd

# Ruta de la base de datos. Se puede cambiar con la variable de entorno RUTA_DB
# (útil para pruebas y para el despliegue).
RUTA_DB = os.environ.get("RUTA_DB", "transporte.db")

# Nombres iguales a las columnas del Excel para que todo coincida.
PLATAFORMAS_BASE = ["Didi", "InDrive", "Uber", "Extras"]
CATEGORIAS_BASE = ["Gasolina", "Apps", "Comida", "Otros Gastos"]
METODOS_BASE = ["Efectivo", "Nequi"]

# grupo -> (nombre de la columna en la tabla, nombres base)
GRUPOS = {
    "ingresos": ("plataforma", PLATAFORMAS_BASE),
    "gastos": ("categoria", CATEGORIAS_BASE),
    "movimientos": ("metodo", METODOS_BASE),
}


# ---------------------------------------------------------------------------
# Conexión
# ---------------------------------------------------------------------------
@contextmanager
def _conexion():
    """Abre la base, confirma los cambios al terminar y la cierra siempre."""
    conn = sqlite3.connect(RUTA_DB)
    conn.execute("PRAGMA foreign_keys = ON")  # necesario para ON DELETE CASCADE
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()  # si algo falla, no queda nada a medias
        raise
    finally:
        conn.close()


def _entero(valor):
    """Convierte cualquier valor a pesos enteros. Vacío o inválido = 0."""
    try:
        if valor is None or pd.isna(valor):
            return 0
        return int(round(float(valor)))
    except (TypeError, ValueError):
        return 0


# ---------------------------------------------------------------------------
# Creación de tablas
# ---------------------------------------------------------------------------
def init_db():
    """Crea las tablas nuevas si no existen. No toca la tabla vieja 'registros'."""
    with _conexion() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS dias_trabajo (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha         TEXT NOT NULL UNIQUE,      -- formato AAAA-MM-DD
                observaciones TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS ingresos (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                dia_id     INTEGER NOT NULL REFERENCES dias_trabajo(id) ON DELETE CASCADE,
                plataforma TEXT NOT NULL,
                valor      INTEGER NOT NULL,
                UNIQUE (dia_id, plataforma)
            );

            CREATE TABLE IF NOT EXISTS gastos (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                dia_id    INTEGER NOT NULL REFERENCES dias_trabajo(id) ON DELETE CASCADE,
                categoria TEXT NOT NULL,
                valor     INTEGER NOT NULL,
                UNIQUE (dia_id, categoria)
            );

            CREATE TABLE IF NOT EXISTS movimientos (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                dia_id INTEGER NOT NULL REFERENCES dias_trabajo(id) ON DELETE CASCADE,
                metodo TEXT NOT NULL,
                valor  INTEGER NOT NULL,
                UNIQUE (dia_id, metodo)
            );
        """)


# ---------------------------------------------------------------------------
# Guardar y leer un día
# ---------------------------------------------------------------------------
def _guardar_dia_en(conn, fecha, ingresos, gastos, movimientos, observaciones):
    """Guarda un día completo dentro de una conexión ya abierta.

    Si la fecha ya existe, REEMPLAZA sus valores (así editar un día o subir el
    mismo Excel dos veces no duplica nada). Los valores en 0 no se guardan.
    """
    fecha = str(fecha)
    conn.execute(
        """
        INSERT INTO dias_trabajo (fecha, observaciones) VALUES (?, ?)
        ON CONFLICT(fecha) DO UPDATE SET observaciones = excluded.observaciones
        """,
        (fecha, observaciones or ""),
    )
    dia_id = conn.execute(
        "SELECT id FROM dias_trabajo WHERE fecha = ?", (fecha,)
    ).fetchone()[0]

    for grupo, valores in (
        ("ingresos", ingresos),
        ("gastos", gastos),
        ("movimientos", movimientos),
    ):
        columna = GRUPOS[grupo][0]
        conn.execute(f"DELETE FROM {grupo} WHERE dia_id = ?", (dia_id,))
        for nombre, valor in (valores or {}).items():
            v = _entero(valor)
            if v != 0:
                conn.execute(
                    f"INSERT INTO {grupo} (dia_id, {columna}, valor) VALUES (?, ?, ?)",
                    (dia_id, str(nombre).strip(), v),
                )


def guardar_dia(fecha, ingresos, gastos, movimientos, observaciones=""):
    """Guarda (o reemplaza) un día.

    Ejemplo:
        guardar_dia("2025-08-01",
                    ingresos={"InDrive": 42439, "Uber": 33093, "Extras": 12000},
                    gastos={"Gasolina": 60000, "Apps": 17000},
                    movimientos={"Efectivo": 16000, "Nequi": 98400})
    """
    with _conexion() as conn:
        _guardar_dia_en(conn, fecha, ingresos, gastos, movimientos, observaciones)


def cargar_dia(fecha):
    """Devuelve un diccionario con el día, o None si no existe."""
    with _conexion() as conn:
        dia = conn.execute(
            "SELECT id, observaciones FROM dias_trabajo WHERE fecha = ?",
            (str(fecha),),
        ).fetchone()
        if dia is None:
            return None
        resultado = {"fecha": str(fecha), "observaciones": dia[1]}
        for grupo, (columna, _) in GRUPOS.items():
            filas = conn.execute(
                f"SELECT {columna}, valor FROM {grupo} WHERE dia_id = ?", (dia[0],)
            ).fetchall()
            resultado[grupo] = {nombre: valor for nombre, valor in filas}
        return resultado


def eliminar_dia(fecha):
    """Borra un día y todos sus valores (ON DELETE CASCADE)."""
    with _conexion() as conn:
        conn.execute("DELETE FROM dias_trabajo WHERE fecha = ?", (str(fecha),))


def nombres_disponibles(grupo):
    """Nombres base + los que se hayan agregado después (para armar el formulario)."""
    columna, base = GRUPOS[grupo]
    with _conexion() as conn:
        filas = conn.execute(
            f"SELECT DISTINCT {columna} FROM {grupo} ORDER BY {columna}"
        ).fetchall()
    return base + sorted(f[0] for f in filas if f[0] not in base)


# ---------------------------------------------------------------------------
# Resumen: una fila por día, con el mismo formato del Excel
# ---------------------------------------------------------------------------
def resumen_dias(desde=None, hasta=None):
    """Devuelve un DataFrame con una fila por día y las mismas columnas del Excel.

    Columnas: Fecha, <plataformas>, Total Ingresos, <gastos>, Total Gastos,
    Ganancia Est, <métodos>, Total Disp, Diferencia, Observaciones.

    Diferencia = Ganancia Est - Total Disp (misma fórmula del Excel).
    'desde' y 'hasta' son fechas opcionales (inclusive).
    """
    filtros, params = [], []
    if desde:
        filtros.append("d.fecha >= ?")
        params.append(str(desde))
    if hasta:
        filtros.append("d.fecha <= ?")
        params.append(str(hasta))
    where = ("WHERE " + " AND ".join(filtros)) if filtros else ""

    with _conexion() as conn:
        dias = pd.read_sql_query(
            f"SELECT d.fecha AS Fecha, d.observaciones AS Observaciones "
            f"FROM dias_trabajo d {where} ORDER BY d.fecha",
            conn,
            params=params,
        )
        anchos = {}
        for grupo, (columna, base) in GRUPOS.items():
            largo = pd.read_sql_query(
                f"SELECT d.fecha AS Fecha, t.{columna} AS nombre, t.valor "
                f"FROM {grupo} t JOIN dias_trabajo d ON d.id = t.dia_id {where}",
                conn,
                params=params,
            )
            ancho = largo.pivot_table(
                index="Fecha", columns="nombre", values="valor", aggfunc="sum"
            )
            nuevos = sorted(c for c in ancho.columns if c not in base)
            anchos[grupo] = ancho.reindex(columns=base + nuevos)

    resumen = dias.set_index("Fecha")
    observaciones = resumen.pop("Observaciones")
    for grupo in GRUPOS:
        resumen = resumen.join(anchos[grupo])
    resumen = resumen.fillna(0).astype(int)

    cols_ing = list(anchos["ingresos"].columns)
    cols_gas = list(anchos["gastos"].columns)
    cols_mov = list(anchos["movimientos"].columns)

    resumen["Total Ingresos"] = resumen[cols_ing].sum(axis=1)
    resumen["Total Gastos"] = resumen[cols_gas].sum(axis=1)
    resumen["Ganancia Est"] = resumen["Total Ingresos"] - resumen["Total Gastos"]
    resumen["Total Disp"] = resumen[cols_mov].sum(axis=1)
    resumen["Diferencia"] = resumen["Ganancia Est"] - resumen["Total Disp"]
    resumen["Observaciones"] = observaciones

    orden = (
        cols_ing + ["Total Ingresos"]
        + cols_gas + ["Total Gastos", "Ganancia Est"]
        + cols_mov + ["Total Disp", "Diferencia", "Observaciones"]
    )
    return resumen[orden].reset_index()


# ---------------------------------------------------------------------------
# Migración de los datos de la tabla vieja 'registros'
# ---------------------------------------------------------------------------
def migrar_registros_antiguos():
    """Copia los días de la tabla vieja 'registros' a las tablas nuevas.

    - NO borra ni modifica la tabla vieja.
    - Solo copia fechas que todavía no existen en el sistema nuevo, así que se
      puede ejecutar varias veces sin pisar datos editados después.
    Devuelve (migrados, omitidos).
    """
    with _conexion() as conn:
        existe = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='registros'"
        ).fetchone()
        if existe is None:
            return 0, 0

        filas = conn.execute(
            "SELECT fecha, didi, indrive, uber, extras, gasolina, apps, comida, "
            "otros_gastos, efectivo, nequi FROM registros ORDER BY fecha"
        ).fetchall()

        migrados = omitidos = 0
        for (fecha, didi, indrive, uber, extras, gasolina, apps, comida,
             otros, efectivo, nequi) in filas:
            ya_existe = conn.execute(
                "SELECT 1 FROM dias_trabajo WHERE fecha = ?", (fecha,)
            ).fetchone()
            if ya_existe:
                omitidos += 1
                continue
            _guardar_dia_en(
                conn,
                fecha,
                ingresos={"Didi": didi, "InDrive": indrive, "Uber": uber, "Extras": extras},
                gastos={"Gasolina": gasolina, "Apps": apps, "Comida": comida, "Otros Gastos": otros},
                movimientos={"Efectivo": efectivo, "Nequi": nequi},
                observaciones="",
            )
            migrados += 1
        return migrados, omitidos
