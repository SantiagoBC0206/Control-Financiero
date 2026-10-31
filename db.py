
"""Capa de base de datos del Control Financiero.

Soporta PostgreSQL/Supabase y SQLite para desarrollo local.
Las pantallas de Streamlit utilizan únicamente las funciones de este módulo.
"""

from contextlib import contextmanager
import sqlite3

import pandas as pd
import streamlit as st


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

DATABASE_URL = st.secrets.get("DATABASE_URL", None)

PLATAFORMAS_BASE = ["Didi", "InDrive", "Uber", "Extras"]
CATEGORIAS_BASE = ["Gasolina", "Apps", "Comida", "Otros Gastos"]
METODOS_BASE = ["Efectivo", "Nequi"]

GRUPOS = {
    "ingresos": ("plataforma", PLATAFORMAS_BASE),
    "gastos": ("categoria", CATEGORIAS_BASE),
    "movimientos": ("metodo", METODOS_BASE),
}


# ---------------------------------------------------------------------------
# Identificación del motor de base de datos
# ---------------------------------------------------------------------------

def _es_postgresql(conn):
    """Indica si la conexión corresponde a PostgreSQL."""
    return type(conn).__module__.startswith("psycopg2")


def _placeholder(conn):
    """Devuelve el marcador SQL correspondiente al motor."""
    return "%s" if _es_postgresql(conn) else "?"


# ---------------------------------------------------------------------------
# Conexión y transacciones
# ---------------------------------------------------------------------------

@contextmanager
def _conexion():
    """Abre una conexión y administra su transacción.

    Si DATABASE_URL está configurada, PostgreSQL es obligatorio.
    No se permite cambiar silenciosamente a SQLite ante un fallo.
    SQLite queda disponible para desarrollo local sin DATABASE_URL.
    """

    if DATABASE_URL:
        try:
            import psycopg2
            conn = psycopg2.connect(DATABASE_URL)
        except Exception as e:
            raise RuntimeError(
                "No fue posible conectar con PostgreSQL/Supabase. "
                "No se utilizará SQLite para evitar guardar información "
                "en una base de datos diferente."
            ) from e
    else:
        conn = sqlite3.connect("transporte.db")
        conn.execute("PRAGMA foreign_keys = ON")

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _entero(valor):
    """Convierte cualquier valor a pesos enteros. Vacío o inválido = 0."""
    try:
        if valor is None or pd.isna(valor):
            return 0
        return int(round(float(valor)))
    except (TypeError, ValueError):
        return 0


def _leer_dataframe(conn, consulta, parametros=None):
    """Ejecuta una consulta y devuelve sus resultados como DataFrame."""
    cursor = conn.cursor()
    cursor.execute(consulta, parametros or [])

    filas = cursor.fetchall()
    columnas = [columna[0] for columna in cursor.description]

    return pd.DataFrame(filas, columns=columnas)


# ---------------------------------------------------------------------------
# Inicialización y comprobación de tablas
# ---------------------------------------------------------------------------

def init_db():
    """Inicializa SQLite local o verifica el esquema existente en PostgreSQL.

    En PostgreSQL no se crean ni modifican tablas desde la aplicación.
    La estructura debe existir previamente y administrarse desde Supabase.
    """

    with _conexion() as conn:

        if _es_postgresql(conn):
            tablas_requeridas = [
                "dias_trabajo",
                "ingresos",
                "gastos",
                "movimientos",
            ]

            cursor = conn.cursor()
            faltantes = []

            for tabla in tablas_requeridas:
                cursor.execute(
                    "SELECT to_regclass(%s)",
                    (f"public.{tabla}",)
                )

                if cursor.fetchone()[0] is None:
                    faltantes.append(tabla)

            if faltantes:
                raise RuntimeError(
                    "Faltan tablas necesarias en PostgreSQL: "
                    + ", ".join(faltantes)
                    + ". Deben crearse desde Supabase antes de iniciar "
                    "la aplicación."
                )

            return

        # SQLite: creación de tablas para desarrollo local.
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dias_trabajo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL UNIQUE,
                observaciones TEXT NOT NULL DEFAULT ''
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingresos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dia_id INTEGER NOT NULL
                    REFERENCES dias_trabajo(id) ON DELETE CASCADE,
                plataforma TEXT NOT NULL,
                valor INTEGER NOT NULL,
                UNIQUE (dia_id, plataforma)
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gastos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dia_id INTEGER NOT NULL
                    REFERENCES dias_trabajo(id) ON DELETE CASCADE,
                categoria TEXT NOT NULL,
                valor INTEGER NOT NULL,
                UNIQUE (dia_id, categoria)
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS movimientos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dia_id INTEGER NOT NULL
                    REFERENCES dias_trabajo(id) ON DELETE CASCADE,
                metodo TEXT NOT NULL,
                valor INTEGER NOT NULL,
                UNIQUE (dia_id, metodo)
            );
        """)


# ---------------------------------------------------------------------------
# Guardar y leer un día
# ---------------------------------------------------------------------------

def _guardar_dia_en(conn, fecha, ingresos, gastos, movimientos, observaciones):
    """Guarda un día dentro de una conexión abierta."""

    p = _placeholder(conn)
    cursor = conn.cursor()
    fecha = str(fecha)

    if _es_postgresql(conn):
        cursor.execute(
            f"""
            INSERT INTO dias_trabajo (fecha, observaciones)
            VALUES ({p}, {p})
            ON CONFLICT(fecha)
            DO UPDATE SET observaciones = EXCLUDED.observaciones
            """,
            (fecha, observaciones or ""),
        )
    else:
        cursor.execute(
            f"""
            INSERT INTO dias_trabajo (fecha, observaciones)
            VALUES ({p}, {p})
            ON CONFLICT(fecha)
            DO UPDATE SET observaciones = excluded.observaciones
            """,
            (fecha, observaciones or ""),
        )

    cursor.execute(
        f"SELECT id FROM dias_trabajo WHERE fecha = {p}",
        (fecha,),
    )

    dia_id = cursor.fetchone()[0]

    for grupo, valores in (
        ("ingresos", ingresos),
        ("gastos", gastos),
        ("movimientos", movimientos),
    ):
        columna = GRUPOS[grupo][0]

        cursor.execute(
            f"DELETE FROM {grupo} WHERE dia_id = {p}",
            (dia_id,),
        )

        for nombre, valor in (valores or {}).items():
            v = _entero(valor)

            if v != 0:
                cursor.execute(
                    f"""
                    INSERT INTO {grupo} (dia_id, {columna}, valor)
                    VALUES ({p}, {p}, {p})
                    """,
                    (dia_id, str(nombre).strip(), v),
                )


def guardar_dia(fecha, ingresos, gastos, movimientos, observaciones=""):
    """Guarda o reemplaza un día completo."""

    with _conexion() as conn:
        _guardar_dia_en(
            conn,
            fecha,
            ingresos,
            gastos,
            movimientos,
            observaciones,
        )


def guardar_varios_dias(dias):
    """Guarda una lista de días dentro de una sola transacción."""

    with _conexion() as conn:
        for d in dias:
            _guardar_dia_en(
                conn,
                d["fecha"],
                d["ingresos"],
                d["gastos"],
                d["movimientos"],
                d.get("observaciones", ""),
            )


def cargar_dia(fecha):
    """Devuelve los datos de un día o None si no existe."""

    with _conexion() as conn:
        p = _placeholder(conn)
        cursor = conn.cursor()

        cursor.execute(
            f"""
            SELECT id, observaciones
            FROM dias_trabajo
            WHERE fecha = {p}
            """,
            (str(fecha),),
        )

        dia = cursor.fetchone()

        if dia is None:
            return None

        resultado = {
            "fecha": str(fecha),
            "observaciones": dia[1],
        }

        for grupo, (columna, _) in GRUPOS.items():
            cursor.execute(
                f"""
                SELECT {columna}, valor
                FROM {grupo}
                WHERE dia_id = {p}
                """,
                (dia[0],),
            )

            filas = cursor.fetchall()
            resultado[grupo] = {
                nombre: valor for nombre, valor in filas
            }

        return resultado


def eliminar_dia(fecha):
    """Elimina un día y sus registros asociados."""

    with _conexion() as conn:
        p = _placeholder(conn)

        conn.cursor().execute(
            f"DELETE FROM dias_trabajo WHERE fecha = {p}",
            (str(fecha),),
        )


def nombres_disponibles(grupo):
    """Devuelve plataformas, categorías o métodos disponibles."""

    columna, base = GRUPOS[grupo]

    with _conexion() as conn:
        cursor = conn.cursor()

        cursor.execute(
            f"SELECT DISTINCT {columna} FROM {grupo} ORDER BY {columna}"
        )

        filas = cursor.fetchall()

    return base + sorted(
        f[0] for f in filas if f[0] not in base
    )


# ---------------------------------------------------------------------------
# Resumen general para la aplicación
# ---------------------------------------------------------------------------

def resumen_dias(desde=None, hasta=None):
    """Devuelve un DataFrame con todas las métricas calculadas."""

    with _conexion() as conn:

        p = _placeholder(conn)
        filtros = []
        params = []

        if desde:
            filtros.append(f"d.fecha >= {p}")
            params.append(str(desde))

        if hasta:
            filtros.append(f"d.fecha <= {p}")
            params.append(str(hasta))

        where = (
            "WHERE " + " AND ".join(filtros)
            if filtros else ""
        )

        dias = _leer_dataframe(
            conn,
            f"""
            SELECT d.fecha, d.observaciones
            FROM dias_trabajo d
            {where}
            ORDER BY d.fecha DESC
            """,
            params,
        )

        if dias.empty:
            return pd.DataFrame()

        dias.columns = [c.lower() for c in dias.columns]

        dias = dias.rename(
            columns={
                "fecha": "Fecha",
                "observaciones": "Observaciones",
            }
        )

        anchos = {}

        for grupo, (columna, base) in GRUPOS.items():

            largo = _leer_dataframe(
                conn,
                f"""
                SELECT
                    d.fecha,
                    t.{columna} AS nombre,
                    t.valor
                FROM {grupo} t
                JOIN dias_trabajo d ON d.id = t.dia_id
                {where}
                """,
                params,
            )

            if largo.empty:
                ancho = pd.DataFrame(
                    columns=["Fecha"] + base
                ).set_index("Fecha")
            else:
                largo.columns = [c.lower() for c in largo.columns]

                ancho = largo.pivot_table(
                    index="fecha",
                    columns="nombre",
                    values="valor",
                    aggfunc="sum",
                )

                ancho.index.name = "Fecha"

            nuevos = sorted(
                c for c in ancho.columns if c not in base
            )

            anchos[grupo] = ancho.reindex(
                columns=base + nuevos
            )

        resumen = dias.set_index("Fecha")
        observaciones = resumen.pop("Observaciones")

        for grupo in GRUPOS:
            resumen = resumen.join(anchos[grupo])

        resumen = resumen.fillna(0).astype(int)

        cols_ing = list(anchos["ingresos"].columns)
        cols_gas = list(anchos["gastos"].columns)
        cols_mov = list(anchos["movimientos"].columns)

        resumen["Total Ingresos"] = (
            resumen[cols_ing].sum(axis=1) if cols_ing else 0
        )

        resumen["Total Gastos"] = (
            resumen[cols_gas].sum(axis=1) if cols_gas else 0
        )

        resumen["Ganancia Est"] = (
            resumen["Total Ingresos"] - resumen["Total Gastos"]
        )

        resumen["Total Disp"] = (
            resumen[cols_mov].sum(axis=1) if cols_mov else 0
        )

        resumen["Diferencia"] = (
            resumen["Total Disp"] - resumen["Ganancia Est"]
        )

        resumen["Observaciones"] = observaciones

        orden = (
            cols_ing
            + ["Total Ingresos"]
            + cols_gas
            + ["Total Gastos", "Ganancia Est"]
            + cols_mov
            + ["Total Disp", "Diferencia", "Observaciones"]
        )

        return resumen[orden].reset_index()
