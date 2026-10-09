"""db.py — Capa de base de datos del Control Financiero (Soporta PostgreSQL/Supabase y SQLite).

Aquí vive TODO lo que toca la base de datos. Las pantallas (Streamlit) solo
llaman a estas funciones y nunca escriben SQL directamente.
"""

from contextlib import contextmanager
import sqlite3
import pandas as pd
import streamlit as st

# Obtener la URL de conexión a PostgreSQL desde st.secrets
DATABASE_URL = st.secrets.get("DATABASE_URL", None)

# Nombres iguales a las columnas del Excel para mantener compatibilidad
PLATAFORMAS_BASE = ["Didi", "InDrive", "Uber", "Extras"]
CATEGORIAS_BASE = ["Gasolina", "Apps", "Comida", "Otros Gastos"]
METODOS_BASE = ["Efectivo", "Nequi"]

GRUPOS = {
    "ingresos": ("plataforma", PLATAFORMAS_BASE),
    "gastos": ("categoria", CATEGORIAS_BASE),
    "movimientos": ("metodo", METODOS_BASE),
}


# ---------------------------------------------------------------------------
# Conexión adaptativa (PostgreSQL o SQLite)
# ---------------------------------------------------------------------------
@contextmanager
def _conexion():
  """Abre la base de datos, maneja la transacción y la cierra automáticamente."""
  if DATABASE_URL:
    try:
      import psycopg2

      conn = psycopg2.connect(DATABASE_URL)
    except Exception as e:
      st.warning(f"No se pudo conectar a Supabase/PostgreSQL, usando SQLite: {e}")
      conn = sqlite3.connect("transporte.db")
      conn.execute("PRAGMA foreign_keys = ON")
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


def _placeholder(conn):
  """Retorna el marcador de posición correcto según la base de datos usada."""
  return "%s" if type(conn).__module__.startswith("psycopg2") else "?"


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
  """Crea las tablas relacionales en Supabase/PostgreSQL o SQLite."""
  with _conexion() as conn:
    cursor = conn.cursor()

    if type(conn).__module__.startswith("psycopg2"):
      pk_type = "SERIAL PRIMARY KEY"
    else:
      pk_type = "INTEGER PRIMARY KEY AUTOINCREMENT"

    cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS dias_trabajo (
                id {pk_type},
                fecha TEXT NOT NULL UNIQUE,
                observaciones TEXT NOT NULL DEFAULT ''
            );
        """)

    cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS ingresos (
                id {pk_type},
                dia_id INTEGER NOT NULL REFERENCES dias_trabajo(id) ON DELETE CASCADE,
                plataforma TEXT NOT NULL,
                valor INTEGER NOT NULL,
                UNIQUE (dia_id, plataforma)
            );
        """)

    cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS gastos (
                id {pk_type},
                dia_id INTEGER NOT NULL REFERENCES dias_trabajo(id) ON DELETE CASCADE,
                categoria TEXT NOT NULL,
                valor INTEGER NOT NULL,
                UNIQUE (dia_id, categoria)
            );
        """)

    cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS movimientos (
                id {pk_type},
                dia_id INTEGER NOT NULL REFERENCES dias_trabajo(id) ON DELETE CASCADE,
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

  if type(conn).__module__.startswith("psycopg2"):
    cursor.execute(
        f"""
            INSERT INTO dias_trabajo (fecha, observaciones) VALUES ({p}, {p})
            ON CONFLICT(fecha) DO UPDATE SET observaciones = EXCLUDED.observaciones
        """,
        (fecha, observaciones or ""),
    )
  else:
    cursor.execute(
        f"""
            INSERT INTO dias_trabajo (fecha, observaciones) VALUES ({p}, {p})
            ON CONFLICT(fecha) DO UPDATE SET observaciones = excluded.observaciones
        """,
        (fecha, observaciones or ""),
    )

  cursor.execute(f"SELECT id FROM dias_trabajo WHERE fecha = {p}", (fecha,))
  dia_id = cursor.fetchone()[0]

  for grupo, valores in (
      ("ingresos", ingresos),
      ("gastos", gastos),
      ("movimientos", movimientos),
  ):
    columna = GRUPOS[grupo][0]
    cursor.execute(f"DELETE FROM {grupo} WHERE dia_id = {p}", (dia_id,))

    for nombre, valor in (valores or {}).items():
      v = _entero(valor)
      if v != 0:
        cursor.execute(
            f"INSERT INTO {grupo} (dia_id, {columna}, valor) VALUES ({p}, {p}, {p})",
            (dia_id, str(nombre).strip(), v),
        )


def guardar_dia(fecha, ingresos, gastos, movimientos, observaciones=""):
  """Guarda o reemplaza un día completo."""
  with _conexion() as conn:
    _guardar_dia_en(conn, fecha, ingresos, gastos, movimientos, observaciones)


def guardar_varios_dias(dias):
  """Guarda una lista de días en una sola transacción."""
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
  """Devuelve un diccionario con los datos del día o None si no existe."""
  with _conexion() as conn:
    p = _placeholder(conn)
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT id, observaciones FROM dias_trabajo WHERE fecha = {p}",
        (str(fecha),),
    )
    dia = cursor.fetchone()
    if dia is None:
      return None

    resultado = {"fecha": str(fecha), "observaciones": dia[1]}
    for grupo, (columna, _) in GRUPOS.items():
      cursor.execute(
          f"SELECT {columna}, valor FROM {grupo} WHERE dia_id = {p}",
          (dia[0],),
      )
      filas = cursor.fetchall()
      resultado[grupo] = {nombre: valor for nombre, valor in filas}
    return resultado


def eliminar_dia(fecha):
  """Borra un día y todos sus registros asociados."""
  with _conexion() as conn:
    p = _placeholder(conn)
    conn.cursor().execute(f"DELETE FROM dias_trabajo WHERE fecha = {p}", (str(fecha),))


def nombres_disponibles(grupo):
  """Devuelve plataformas, categorías o métodos disponibles."""
  columna, base = GRUPOS[grupo]
  with _conexion() as conn:
    cursor = conn.cursor()
    cursor.execute(f"SELECT DISTINCT {columna} FROM {grupo} ORDER BY {columna}")
    filas = cursor.fetchall()
  return base + sorted(f[0] for f in filas if f[0] not in base)


# ---------------------------------------------------------------------------
# Resumen general para la aplicación
# ---------------------------------------------------------------------------
def resumen_dias(desde=None, hasta=None):
  """Devuelve un DataFrame estructurado con todas las métricas calculadas."""
  filtros, params = [], []
  if desde:
    filtros.append("d.fecha >= " + ("%s" if DATABASE_URL else "?"))
    params.append(str(desde))
  if hasta:
    filtros.append("d.fecha <= " + ("%s" if DATABASE_URL else "?"))
    params.append(str(hasta))

  where = ("WHERE " + " AND ".join(filtros)) if filtros else ""

  with _conexion() as conn:
    dias = pd.read_sql_query(
        f"SELECT d.fecha, d.observaciones "
        f"FROM dias_trabajo d {where} ORDER BY d.fecha DESC",
        conn,
        params=params,
    )

    if dias.empty:
      return pd.DataFrame()

    # Normalizar nombres de columnas a minúsculas para evitar mismatches en PostgreSQL
    dias.columns = [c.lower() for c in dias.columns]
    dias = dias.rename(columns={"fecha": "Fecha", "observaciones": "Observaciones"})

    anchos = {}
    for grupo, (columna, base) in GRUPOS.items():
      largo = pd.read_sql_query(
          f"SELECT d.fecha, t.{columna} AS nombre, t.valor "
          f"FROM {grupo} t JOIN dias_trabajo d ON d.id = t.dia_id {where}",
          conn,
          params=params,
      )

      if largo.empty:
        ancho = pd.DataFrame(columns=["Fecha"] + base).set_index("Fecha")
      else:
        largo.columns = [c.lower() for c in largo.columns]
        ancho = largo.pivot_table(
            index="fecha", columns="nombre", values="valor", aggfunc="sum"
        )
        ancho.index.name = "Fecha"

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

  resumen["Total Ingresos"] = resumen[cols_ing].sum(axis=1) if cols_ing else 0
  resumen["Total Gastos"] = resumen[cols_gas].sum(axis=1) if cols_gas else 0
  resumen["Ganancia Est"] = resumen["Total Ingresos"] - resumen["Total Gastos"]
  resumen["Total Disp"] = resumen[cols_mov].sum(axis=1) if cols_mov else 0
  resumen["Diferencia"] = resumen["Total Disp"] - resumen["Ganancia Est"]
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