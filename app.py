from datetime import datetime, date
import os
import re
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Control Financiero - Conductor",
    page_icon="🚗",
    layout="centered",
    initial_sidebar_state="expanded",
)


# --- 1. CONFIGURACIÓN DE SEGURIDAD MEDIANTE SECRETS ---
def verificar_password():
  try:
    password_correcta = st.secrets["passwords"]["admin_password"]
  except Exception:
    password_correcta = "tupapa2026"

  def password_entered():
    if st.session_state["password_input"] == password_correcta:
      st.session_state["password_correct"] = True
      del st.session_state["password_input"]
    else:
      st.session_state["password_correct"] = False

  if "password_correct" not in st.session_state:
    st.title("🔒 Control Financiero")
    st.markdown("##### Acceso Privado")
    st.text_input(
        "Ingresa la contraseña secreta",
        type="password",
        on_change=password_entered,
        key="password_input",
    )
    return False
  elif not st.session_state["password_correct"]:
    st.title("🔒 Control Financiero")
    st.markdown("##### Acceso Privado")
    st.text_input(
        "Ingresa la contraseña secreta",
        type="password",
        on_change=password_entered,
        key="password_input",
    )
    st.error("😕 Contraseña incorrecta")
    return False
  else:
    return True


if not verificar_password():
  st.stop()


# --- 2. BASE DE DATOS RELACIONAL ---
DB_NAME = "transporte_v2.db"


def get_connection():
  return sqlite3.connect(DB_NAME)


def init_db():
  conn = get_connection()
  cursor = conn.cursor()

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS dias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT UNIQUE NOT NULL,
            observaciones TEXT
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS ingresos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dia_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            valor REAL NOT NULL,
            FOREIGN KEY (dia_id) REFERENCES dias (id) ON DELETE CASCADE
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS gastos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dia_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            valor REAL NOT NULL,
            FOREIGN KEY (dia_id) REFERENCES dias (id) ON DELETE CASCADE
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS recepciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dia_id INTEGER NOT NULL,
            metodo TEXT NOT NULL,
            valor REAL NOT NULL,
            FOREIGN KEY (dia_id) REFERENCES dias (id) ON DELETE CASCADE
        )
    """)

  conn.commit()
  conn.close()


init_db()


# --- 3. FUNCIONES DE LECTURA Y ESCRITURA EN BASE DE DATOS ---
def obtener_datos_completos():
  conn = get_connection()
  query = """
    SELECT d.fecha,
           COALESCE(SUM(CASE WHEN i.tipo = 'Didi' THEN i.valor END), 0) as didi,
           COALESCE(SUM(CASE WHEN i.tipo = 'InDrive' THEN i.valor END), 0) as indrive,
           COALESCE(SUM(CASE WHEN i.tipo = 'Uber' THEN i.valor END), 0) as uber,
           COALESCE(SUM(CASE WHEN i.tipo = 'Extras' THEN i.valor END), 0) as extras,
           COALESCE(SUM(CASE WHEN g.tipo = 'Gasolina' THEN g.valor END), 0) as gasolina,
           COALESCE(SUM(CASE WHEN g.tipo = 'Apps' THEN g.valor END), 0) as apps,
           COALESCE(SUM(CASE WHEN g.tipo = 'Comida' THEN g.valor END), 0) as comida,
           COALESCE(SUM(CASE WHEN g.tipo = 'Otros Gastos' THEN g.valor END), 0) as otros_gastos,
           COALESCE(SUM(CASE WHEN r.metodo = 'Efectivo' THEN r.valor END), 0) as efectivo,
           COALESCE(SUM(CASE WHEN r.metodo = 'Nequi / Bancos' THEN r.valor END), 0) as nequi
    FROM dias d
    LEFT JOIN ingresos i ON d.id = i.dia_id
    LEFT JOIN gastos g ON d.id = g.dia_id
    LEFT JOIN recepciones r ON d.id = r.dia_id
    GROUP BY d.id, d.fecha
    ORDER BY d.fecha DESC
    """
  df = pd.read_sql_query(query, conn)
  conn.close()
  if not df.empty:
    df["total_ingresos"] = (
        df["didi"] + df["indrive"] + df["uber"] + df["extras"]
    )
    df["total_gastos"] = (
        df["gasolina"] + df["apps"] + df["comida"] + df["otros_gastos"]
    )
    df["ganancia_neta"] = df["total_ingresos"] - df["total_gastos"]
    df["total_disponible"] = df["efectivo"] + df["nequi"]
    df["diferencia"] = df["total_disponible"] - df["ganancia_neta"]
  return df


def guardar_dia_relacional(fecha_str, dic_ingresos, dic_gastos, dic_recepciones):
  conn = get_connection()
  cursor = conn.cursor()

  cursor.execute(
      "INSERT OR IGNORE INTO dias (fecha) VALUES (?)", (fecha_str,)
  )
  cursor.execute("SELECT id FROM dias WHERE fecha = ?", (fecha_str,))
  dia_id = cursor.fetchone()[0]

  cursor.execute("DELETE FROM ingresos WHERE dia_id = ?", (dia_id,))
  cursor.execute("DELETE FROM gastos WHERE dia_id = ?", (dia_id,))
  cursor.execute("DELETE FROM recepciones WHERE dia_id = ?", (dia_id,))

  for tipo, valor in dic_ingresos.items():
    if valor > 0:
      cursor.execute(
          "INSERT INTO ingresos (dia_id, tipo, valor) VALUES (?, ?, ?)",
          (dia_id, tipo, valor),
      )

  for tipo, valor in dic_gastos.items():
    if valor > 0:
      cursor.execute(
          "INSERT INTO gastos (dia_id, tipo, valor) VALUES (?, ?, ?)",
          (dia_id, tipo, valor),
      )

  for metodo, valor in dic_recepciones.items():
    if valor > 0:
      cursor.execute(
          "INSERT INTO recepciones (dia_id, metodo, valor) VALUES (?, ?, ?)",
          (dia_id, metodo, valor),
      )

  conn.commit()
  conn.close()


# --- 4. ALIAS Y FUZZY MATCHING PARA EXCEL ---
ALIAS_MAP = {
    "didi": ["didi"],
    "indrive": ["indrive", "in drive", "indriver"],
    "uber": ["uber"],
    "extras": ["extras", "extra", "varios ingresos"],
    "gasolina": ["gasolina", "combustible", "gasolinera"],
    "apps": ["apps", "comision", "comisiones", "base"],
    "comida": ["comida", "almuerzo", "alimentacion"],
    "otros_gastos": [
        "otros gastos",
        "otros_gastos",
        "otros",
        "gastos varios",
        "varios gastos",
        "varios",
    ],
    "efectivo": ["efectivo", "efectivo recibido"],
    "nequi": ["nequi", "nequi / bancos", "bancos", "transferencia", "banco"],
}


def identificar_columna(nombre_columna_excel):
  col_clean = (
      re.sub(r"[^\w\s]", "", str(nombre_columna_excel)).strip().lower()
  )
  for clave_oficial, lista_alias in ALIAS_MAP.items():
    if col_clean in lista_alias or any(
        col_clean == alias for alias in lista_alias
    ):
      return clave_oficial
  return None


def clean_number(val):
  if pd.isna(val):
    return 0.0
  if isinstance(val, (int, float)):
    return float(val)
  try:
    s = (
        str(val)
        .replace("$", "")
        .replace(".", "")
        .replace(",", "")
        .strip()
    )
    return float(s)
  except Exception:
    return 0.0


# --- 5. INTERFAZ PRINCIPAL Y NAVEGACIÓN ---
st.title("🚗 Control Financiero")

df_general = obtener_datos_completos()

menu = st.sidebar.selectbox(
    "Menú Principal",
    [
        "📊 Dashboard",
        "📱 Registro Diario",
        "📅 Reporte Mensual",
        "📈 Reporte Anual",
        "📥 Importar Historial Excel",
    ],
)

# --- NAVEGACIÓN 1: DASHBOARD ---
if menu == "📊 Dashboard":
  st.subheader("📊 Resumen e Indicadores")

  # Métrica de Hoy
  hoy_str = str(date.today())
  df_hoy = (
      df_general[df_general["fecha"] == hoy_str]
      if not df_general.empty
      else pd.DataFrame()
  )

  st.markdown(f"### 📅 Hoy ({hoy_str})")
  if not df_hoy.empty:
    r_hoy = df_hoy.iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Ingresos", f"${r_hoy['total_ingresos']:,.0f}")
    c2.metric("📉 Gastos", f"${r_hoy['total_gastos']:,.0f}")
    c3.metric("🟢 Ganancia", f"${r_hoy['ganancia_neta']:,.0f}")

    with st.expander("🔍 Ver desglose de hoy"):
      st.write(
          f"**Didi:** ${r_hoy['didi']:,.0f} | **InDrive:**"
          f" ${r_hoy['indrive']:,.0f} \vert{} **Uber:**${r_hoy['uber']:,.0f} |"
          f" **Extras:** ${r_hoy['extras']:,.0f}"
      )
      st.write(
          f"**Gasolina:** ${r_hoy['gasolina']:,.0f} | **Apps:**"
          f" ${r_hoy['apps']:,.0f} \vert{} **Comida:**${r_hoy['comida']:,.0f} |"
          f" **Otros:** ${r_hoy['otros_gastos']:,.0f}"
      )
  else:
    st.info("Aún no se han registrado datos para el día de hoy.")

  st.markdown("---")

  # Acumulado del Mes Actual
  st.markdown("### 📅 Este Mes")
  if not df_general.empty:
    df_general["fecha_dt"] = pd.to_datetime(df_general["fecha"])
    mes_actual = datetime.now().strftime("%Y-%m")
    df_mes = df_general[
        df_general["fecha_dt"].dt.strftime("%Y-%m") == mes_actual
    ]

    if not df_mes.empty:
      t_ing = df_mes["total_ingresos"].sum()
      t_gas = df_mes["total_gastos"].sum()
      t_gan = df_mes["ganancia_neta"].sum()
      dias_trab = len(df_mes[df_mes["total_ingresos"] > 0])
      prom_diario = t_ing / dias_trab if dias_trab > 0 else 0

      m1, m2, m3 = st.columns(3)
      m1.metric("Ingresos Acumulados", f"${t_ing:,.0f}")
      m2.metric("Gastos Acumulados", f"${t_gas:,.0f}")
      m3.metric("Ganancia Acumulada", f"${t_gan:,.0f}")

      st.markdown(
          f"**Días Trabajados:** `{dias_trab}` | **Promedio Diario Ingreso:**"
          f" `${prom_diario:,.0f}`"
      )
    else:
      st.info("Sin registros en el mes actual.")
  else:
    st.info("Sin registros en el sistema.")


# --- NAVEGACIÓN 2: REGISTRO DIARIO MÓVIL ---
elif menu == "📱 Registro Diario":
  st.subheader("📱 Registro Diario de Trabajo")
  fecha_sel = st.date_input("Fecha de trabajo", value=date.today())
  fecha_sel_str = str(fecha_sel)

  # Cargar datos existentes si la fecha ya tiene registro
  match = (
      df_general[df_general["fecha"] == fecha_sel_str]
      if not df_general.empty
      else pd.DataFrame()
  )
  val_exist = match.iloc[0].to_dict() if not match.empty else {}

  with st.form("form_diario_movil"):
    st.markdown("#### 📥 INGRESOS ($)")
    col1, col2 = st.columns(2)
    with col1:
      didi_txt = st.text_input(
          "Didi",
          value=(
              str(int(val_exist.get("didi", 0)))
              if val_exist.get("didi", 0) > 0
              else ""
          ),
      )
      indrive_txt = st.text_input(
          "InDrive",
          value=(
              str(int(val_exist.get("indrive", 0)))
              if val_exist.get("indrive", 0) > 0
              else ""
          ),
      )
    with col2:
      uber_txt = st.text_input(
          "Uber",
          value=(
              str(int(val_exist.get("uber", 0)))
              if val_exist.get("uber", 0) > 0
              else ""
          ),
      )
      extras_txt = st.text_input(
          "Extras",
          value=(
              str(int(val_exist.get("extras", 0)))
              if val_exist.get("extras", 0) > 0
              else ""
          ),
      )

    st.markdown("#### 📤 GASTOS ($)")
    col3, col4 = st.columns(2)
    with col3:
      gasolina_txt = st.text_input(
          "Gasolina",
          value=(
              str(int(val_exist.get("gasolina", 0)))
              if val_exist.get("gasolina", 0) > 0
              else ""
          ),
      )
      apps_txt = st.text_input(
          "Apps (Comisiones/Base)",
          value=(
              str(int(val_exist.get("apps", 0)))
              if val_exist.get("apps", 0) > 0
              else ""
          ),
      )
    with col4:
      comida_txt = st.text_input(
          "Comida",
          value=(
              str(int(val_exist.get("comida", 0)))
              if val_exist.get("comida", 0) > 0
              else ""
          ),
      )
      otros_txt = st.text_input(
          "Otros gastos",
          value=(
              str(int(val_exist.get("otros_gastos", 0)))
              if val_exist.get("otros_gastos", 0) > 0
              else ""
          ),
      )

    st.markdown("#### 💳 DINERO RECIBIDO ($)")
    col5, col6 = st.columns(2)
    with col5:
      efectivo_txt = st.text_input(
          "Efectivo",
          value=(
              str(int(val_exist.get("efectivo", 0)))
              if val_exist.get("efectivo", 0) > 0
              else ""
          ),
      )
    with col6:
      nequi_txt = st.text_input(
          "Nequi / Bancos",
          value=(
              str(int(val_exist.get("nequi", 0)))
              if val_exist.get("nequi", 0) > 0
              else ""
          ),
      )

    submitted = st.form_submit_button(
        "💾 Guardar Día de Trabajo", use_container_width=True
    )

    if submitted:

      def parse_val(v):
        try:
          return float(v.replace(",", "").replace(".", "").strip())
        except:
          return 0.0

      ing = {
          "Didi": parse_val(didi_txt),
          "InDrive": parse_val(indrive_txt),
          "Uber": parse_val(uber_txt),
          "Extras": parse_val(extras_txt),
      }
      gas = {
          "Gasolina": parse_val(gasolina_txt),
          "Apps": parse_val(apps_txt),
          "Comida": parse_val(comida_txt),
          "Otros Gastos": parse_val(otros_txt),
      }
      rec = {
          "Efectivo": parse_val(efectivo_txt),
          "Nequi / Bancos": parse_val(nequi_txt),
      }

      guardar_dia_relacional(fecha_sel_str, ing, gas, rec)
      st.success(f"✅ ¡Guardado exitosamente para el día {fecha_sel_str}!")
      st.rerun()


# --- NAVEGACIÓN 3: REPORTE MENSUAL ---
elif menu == "📅 Reporte Mensual":
  st.subheader("📅 Reporte Mensual Consolidado")

  if df_general.empty:
    st.info("Sin datos para generar reportes.")
  else:
    df_general["fecha_dt"] = pd.to_datetime(df_general["fecha"])
    df_general["AÑO_MES"] = df_general["fecha_dt"].dt.strftime("%Y-%m")
    meses = sorted(df_general["AÑO_MES"].unique(), reverse=True)

    mes_sel = st.selectbox("Selecciona el Mes a Consultar", meses)
    df_mes = df_general[df_general["AÑO_MES"] == mes_sel]

    t_ing = df_mes["total_ingresos"].sum()
    t_gas = df_mes["total_gastos"].sum()
    gan = t_ing - t_gas
    disp = df_mes["total_disponible"].sum()

    st.markdown(f"### 📊 Consolidado de `{mes_sel}`")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Ingresos", f"${t_ing:,.0f}")
    k2.metric("Gastos", f"${t_gas:,.0f}")
    k3.metric("Ganancia", f"${gan:,.0f}")
    k4.metric("Disponible", f"${disp:,.0f}")

    st.markdown("---")
    st.markdown("### Tabla Detallada por Día")
    st.dataframe(
        df_mes[[
            "fecha",
            "didi",
            "indrive",
            "uber",
            "extras",
            "total_ingresos",
            "gasolina",
            "apps",
            "comida",
            "otros_gastos",
            "total_gastos",
            "ganancia_neta",
            "efectivo",
            "nequi",
            "total_disponible",
        ]],
        use_container_width=True,
    )


# --- NAVEGACIÓN 4: REPORTE ANUAL ---
elif menu == "📈 Reporte Anual":
  st.subheader("📈 Reporte Anual y Tendencias")

  if df_general.empty:
    st.info("Sin datos para calcular el reporte anual.")
  else:
    df_general["fecha_dt"] = pd.to_datetime(df_general["fecha"])
    df_general["AÑO"] = df_general["fecha_dt"].dt.strftime("%Y")
    df_general["AÑO_MES"] = df_general["fecha_dt"].dt.strftime("%Y-%m")

    anios = sorted(df_general["AÑO"].unique(), reverse=True)
    anio_sel = st.selectbox("Selecciona el Año", anios)

    df_anio = df_general[df_general["AÑO"] == anio_sel]

    resumen_mensual = (
        df_anio.groupby("AÑO_MES")
        .agg({
            "total_ingresos": "sum",
            "total_gastos": "sum",
            "ganancia_neta": "sum",
            "total_disponible": "sum",
        })
        .reset_index()
    )

    t_ing_anual = resumen_mensual["total_ingresos"].sum()
    t_gas_anual = resumen_mensual["total_gastos"].sum()
    gan_anual = t_ing_anual - t_gas_anual
    prom_mensual = gan_anual / len(resumen_mensual) if not resumen_mensual.empty else 0

    mejor_mes_row = resumen_mensual.loc[
        resumen_mensual["ganancia_neta"].idxmax()
    ]
    mejor_mes_nombre = mejor_mes_row["AÑO_MES"]
    mejor_mes_ganancia = mejor_mes_row["ganancia_neta"]

    st.markdown(f"### 🏆 Resultados de `{anio_sel}`")
    a1, a2, a3 = st.columns(3)
    a1.metric("💰 Ganancia Anual Total", f"${gan_anual:,.0f}")
    a2.metric("📊 Promedio Ganancia Mensual", f"${prom_mensual:,.0f}")
    a3.metric(
        "🏆 Mejor Mes",
        f"{mejor_mes_nombre}",
        f"${mejor_mes_ganancia:,.0f} ganancia",
    )

    st.markdown("---")
    st.markdown("### 📈 Evolución Mensual")
    fig = px.bar(
        resumen_mensual,
        x="AÑO_MES",
        y=["total_ingresos", "total_gastos", "ganancia_neta"],
        barmode="group",
        labels={"value": "Pesos ($)", "AÑO_MES": "Mes", "variable": "Concepto"},
        title=f"Ingresos vs Gastos vs Ganancia ({anio_sel})",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Tabla Consolidada por Mes")
    st.dataframe(resumen_mensual, use_container_width=True)


# --- NAVEGACIÓN 5: IMPORTAR EXCEL ---
elif menu == "📥 Importar Historial Excel":
  st.subheader("📥 Importar Historial de Excel / CSV")
  st.markdown(
      "Sube tus archivos mensuales antiguos. El sistema reconocerá las"
      " columnas automáticamente, ignorará los totales y organizará la base"
      " de datos relacional."
  )

  col_m1, col_m2 = st.columns(2)
  with col_m1:
    anio = st.number_input(
        "Año fallback (si el Excel no trae año)",
        min_value=2020,
        max_value=2030,
        value=2025,
    )
  with col_m2:
    mes = st.selectbox(
        "Mes fallback (si el Excel no trae mes)",
        options=list(range(1, 13)),
        format_func=lambda x: [
            "Enero",
            "Febrero",
            "Marzo",
            "Abril",
            "Mayo",
            "Junio",
            "Julio",
            "Agosto",
            "Septiembre",
            "Octubre",
            "Noviembre",
            "Diciembre",
        ][x - 1],
        index=7,
    )

  archivos_subidos = st.file_uploader(
      "Selecciona uno o varios archivos (.xlsx o .csv)",
      type=["xlsx", "xls", "csv"],
      accept_multiple_files=True,
  )

  if archivos_subidos:
    for archivo in archivos_subidos:
      st.markdown("---")
      st.write(f"📄 **Archivo:** `{archivo.name}`")

      try:
        if archivo.name.endswith(".csv"):
          df_excel = pd.read_csv(archivo)
        else:
          df_excel = pd.read_excel(archivo)

        mapa_cols = {}
        for c in df_excel.columns:
          identificada = identificar_columna(c)
          if identificada:
            mapa_cols[c] = identificada

        st.caption(f"Columnas identificadas: {list(mapa_cols.values())}")
        st.dataframe(df_excel.head(3), use_container_width=True)

        if st.button(
            f"🚀 Procesar e Importar `{archivo.name}`", key=archivo.name
        ):
          dias_importados = 0

          for _, row in df_excel.iterrows():
            val_col0 = str(row.iloc[0]).strip().lower()

            if not val_col0 or val_col0 in ["nan", "none"]:
              continue

            if any(
                k in val_col0 for k in ["total", "mes", "promedio", "suma"]
            ):
              continue

            fecha_final = None
            try:
              dt = pd.to_datetime(row.iloc[0], errors="coerce")
              if pd.notna(dt):
                fecha_final = str(dt.date())
            except Exception:
              pass

            if not fecha_final:
              try:
                if "-" in val_col0:
                  dia_num = int(val_col0.split("-")[-1][:2])
                else:
                  dia_num = int(float(val_col0))
                if 1 <= dia_num <= 31:
                  fecha_final = f"{anio:04d}-{mes:02d}-{dia_num:02d}"
              except Exception:
                continue

            if not fecha_final:
              continue

            ingresos = {
                "Didi": 0.0,
                "InDrive": 0.0,
                "Uber": 0.0,
                "Extras": 0.0,
            }
            gastos = {
                "Gasolina": 0.0,
                "Apps": 0.0,
                "Comida": 0.0,
                "Otros Gastos": 0.0,
            }
            recepciones = {"Efectivo": 0.0, "Nequi / Bancos": 0.0}

            for col_orig, clave_oficial in mapa_cols.items():
              val = clean_number(row[col_orig])

              if clave_oficial == "didi":
                ingresos["Didi"] = val
              elif clave_oficial == "indrive":
                ingresos["InDrive"] = val
              elif clave_oficial == "uber":
                ingresos["Uber"] = val
              elif clave_oficial == "extras":
                ingresos["Extras"] = val
              elif clave_oficial == "gasolina":
                gastos["Gasolina"] = val
              elif clave_oficial == "apps":
                gastos["Apps"] = val
              elif clave_oficial == "comida":
                gastos["Comida"] = val
              elif clave_oficial == "otros_gastos":
                gastos["Otros Gastos"] = val
              elif clave_oficial == "efectivo":
                recepciones["Efectivo"] = val
              elif clave_oficial == "nequi":
                recepciones["Nequi / Bancos"] = val

            guardar_dia_relacional(
                fecha_final, ingresos, gastos, recepciones
            )
            dias_importados += 1

          st.success(
              f"🎉 ¡Éxito! Se registraron/actualizaron {dias_importados} días"
              f" desde `{archivo.name}`."
          )
          st.rerun()

      except Exception as e:
        st.error(f"Error al leer `{archivo.name}`: {e}")