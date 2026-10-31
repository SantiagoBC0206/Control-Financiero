
import io

import pandas as pd
import streamlit as st

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

import db
import estadisticas as est
from utilidades import pesos, hoy, nombre_mes


# =========================================================
# EXPORTACIÓN A EXCEL
# =========================================================

def convertir_df_a_excel(df):
    """
    Genera un archivo Excel con los registros del período.

    Los valores acumulables se suman.
    Efectivo y Nequi representan los saldos del último día.
    Total Disp y Diferencia conservan la suma de los días.
    """

    df = est.preparar(df)

    if df.empty:
        return None

    df_export = df.copy()

    columnas_auxiliares = [
        "Trabajado",
        "AñoMes",
        "Fecha_dt",
        "Dia_Semana",
        "Dia_Semana_ES",
    ]

    df_export = df_export.drop(
        columns=[
            c for c in columnas_auxiliares
            if c in df_export.columns
        ],
        errors="ignore",
    )

    if "Fecha" in df_export.columns:
        df_export["Fecha"] = pd.to_datetime(
            df_export["Fecha"],
            errors="coerce",
        ).dt.strftime("%d/%m/%Y")

    wb = Workbook()
    ws = wb.active
    ws.title = "Control Financiero"

    azul = "17365D"
    azul_claro = "D9EAF7"
    gris = "F2F2F2"
    blanco = "FFFFFF"

    ws.merge_cells(
        start_row=1,
        start_column=1,
        end_row=1,
        end_column=len(df_export.columns),
    )

    titulo = ws.cell(1, 1)
    titulo.value = "REPORTE DE CONTROL FINANCIERO"
    titulo.font = Font(
        bold=True,
        size=15,
        color=blanco,
    )
    titulo.fill = PatternFill(
        "solid",
        fgColor=azul,
    )
    titulo.alignment = Alignment(
        horizontal="center",
        vertical="center",
    )

    ws.row_dimensions[1].height = 30

    fila_encabezados = 3

    for columna, nombre in enumerate(
        df_export.columns,
        start=1,
    ):
        celda = ws.cell(
            fila_encabezados,
            columna,
            nombre,
        )

        celda.font = Font(
            bold=True,
            color=blanco,
        )

        celda.fill = PatternFill(
            "solid",
            fgColor=azul,
        )

        celda.alignment = Alignment(
            horizontal="center",
            vertical="center",
        )

    for fila, registro in enumerate(
        df_export.itertuples(index=False, name=None),
        start=fila_encabezados + 1,
    ):
        for columna, valor in enumerate(
            registro,
            start=1,
        ):
            if pd.isna(valor):
                valor = None

            celda = ws.cell(
                fila,
                columna,
                valor,
            )

            if fila % 2 == 0:
                celda.fill = PatternFill(
                    "solid",
                    fgColor=gris,
                )

    fila_total = fila_encabezados + len(df_export) + 1

    ws.cell(
        fila_total,
        1,
        "TOTALES / SALDOS FINALES",
    )

    ws.cell(
        fila_total,
        1,
    ).font = Font(bold=True)

    ws.cell(
        fila_total,
        1,
    ).fill = PatternFill(
        "solid",
        fgColor=azul_claro,
    )

    columnas_saldo_final = [
        "Efectivo",
        "Nequi",
        "Nequi / Bancos",
        "Bancos",
    ]

    columnas_no_sumar = [
        "Fecha",
        "Observaciones",
    ]

    ultimo_registro = df_export.iloc[-1]

    for columna, nombre in enumerate(
        df_export.columns,
        start=1,
    ):

        if nombre in columnas_no_sumar or columna == 1:
            continue

        valores = pd.to_numeric(
            df_export[nombre],
            errors="coerce",
        ).fillna(0)

        if nombre in columnas_saldo_final:
            total = pd.to_numeric(
                ultimo_registro[nombre],
                errors="coerce",
            )

            total = 0 if pd.isna(total) else total

        else:
            total = valores.sum()

        celda = ws.cell(
            fila_total,
            columna,
            float(total),
        )

        celda.font = Font(bold=True)

        celda.fill = PatternFill(
            "solid",
            fgColor=azul_claro,
        )

    columnas_texto = [
        "Fecha",
        "Observaciones",
    ]

    for columna, nombre in enumerate(
        df_export.columns,
        start=1,
    ):
        if nombre not in columnas_texto:
            for fila in range(
                fila_encabezados + 1,
                fila_total + 1,
            ):
                ws.cell(
                    fila,
                    columna,
                ).number_format = '"$"#,##0'

    for columna, nombre in enumerate(
        df_export.columns,
        start=1,
    ):
        ancho = max(
            len(str(nombre)) + 4,
            14,
        )

        if nombre == "Observaciones":
            ancho = 35

        ws.column_dimensions[
            get_column_letter(columna)
        ].width = ancho

    ws.freeze_panes = "A4"

    ws.auto_filter.ref = (
        f"A{fila_encabezados}:"
        f"{get_column_letter(len(df_export.columns))}"
        f"{fila_encabezados + len(df_export)}"
    )

    borde = Border(
        bottom=Side(
            style="thin",
            color="D9D9D9",
        )
    )

    for fila in ws.iter_rows(
        min_row=fila_encabezados,
        max_row=fila_total,
    ):
        for celda in fila:
            celda.border = borde

    archivo = io.BytesIO()

    wb.save(archivo)
    archivo.seek(0)

    return archivo


# =========================================================
# FUNCIONES AUXILIARES
# =========================================================

def obtener_valor(registro, columna):
    """Obtiene un valor numérico de un registro."""

    if registro is None or columna not in registro.index:
        return 0

    valor = pd.to_numeric(
        registro[columna],
        errors="coerce",
    )

    return 0 if pd.isna(valor) else float(valor)


def fecha_formateada(valor):
    """Convierte una fecha en formato legible."""

    if valor is None or pd.isna(valor):
        return "Sin información"

    return pd.to_datetime(valor).strftime("%d/%m/%Y")


def mostrar_tarjeta_resumen(titulo, valor, ayuda=None):
    """Muestra un indicador financiero."""

    st.metric(
        titulo,
        pesos(valor),
        help=ayuda,
    )


# =========================================================
# PÁGINA PRINCIPAL
# =========================================================

def mostrar():

    st.title("🚗 Control Financiero")

    st.caption(
        "Resumen general de la actividad financiera."
    )

    # -----------------------------------------------------
    # 1. CARGAR INFORMACIÓN
    # -----------------------------------------------------

    try:
        df_original = db.resumen_dias()

    except Exception as e:
        st.error(
            f"No fue posible cargar la información: {e}"
        )
        return

    if df_original is None or df_original.empty:
        st.info(
            "Todavía no hay registros financieros. "
            "Comienza registrando un día para visualizar "
            "el resumen."
        )
        return

    df = est.preparar(df_original)

    if df.empty:
        st.info(
            "No hay registros válidos para mostrar."
        )
        return

    df = df.sort_values("Fecha").reset_index(drop=True)

    fecha_actual = hoy()
    mes_actual = fecha_actual.strftime("%Y-%m")

    # -----------------------------------------------------
    # 2. RESUMEN DEL ÚLTIMO REGISTRO
    # -----------------------------------------------------

    st.markdown("---")
    st.subheader("📅 Resumen del último registro")

    ultimo_registro = df.iloc[-1]

    fecha_ultimo_registro = fecha_formateada(
        ultimo_registro["Fecha"]
    )

    ingresos_ultimo = obtener_valor(
        ultimo_registro,
        "Total Ingresos",
    )

    gastos_ultimo = obtener_valor(
        ultimo_registro,
        "Total Gastos",
    )

    ganancia_ultimo = obtener_valor(
        ultimo_registro,
        "Ganancia Est",
    )

    efectivo_final = obtener_valor(
        ultimo_registro,
        "Efectivo",
    )

    nequi_final = obtener_valor(
        ultimo_registro,
        "Nequi",
    )

    disponible_ultimo = efectivo_final + nequi_final

    st.caption(
        f"Información correspondiente al {fecha_ultimo_registro}."
    )

    c1, c2 = st.columns(2)

    with c1:
        mostrar_tarjeta_resumen(
            "💵 Disponible del último registro",
            disponible_ultimo,
        )

    with c2:
        mostrar_tarjeta_resumen(
            "📈 Ganancia estimada",
            ganancia_ultimo,
        )

    c1, c2 = st.columns(2)

    with c1:
        mostrar_tarjeta_resumen(
            "⬆️ Ingresos del día",
            ingresos_ultimo,
        )

    with c2:
        mostrar_tarjeta_resumen(
            "⬇️ Gastos del día",
            gastos_ultimo,
        )

    # Saldos registrados.

    st.markdown("#### 💳 Saldos registrados")

    c1, c2 = st.columns(2)

    with c1:
        mostrar_tarjeta_resumen(
            "Efectivo",
            efectivo_final,
        )

    with c2:
        mostrar_tarjeta_resumen(
            "Nequi",
            nequi_final,
        )

    # -----------------------------------------------------
    # 3. RESUMEN DEL MES ACTUAL
    # -----------------------------------------------------

    st.markdown("---")
    st.subheader("📊 Resumen del mes")

    df_mes = df[
        df["AñoMes"] == mes_actual
    ].copy()

    if not df_mes.empty:

        ingresos_mes = float(
            df_mes["Total Ingresos"].sum()
        )

        gastos_mes = float(
            df_mes["Total Gastos"].sum()
        )

        ganancia_mes = ingresos_mes - gastos_mes

        disponible_mes = float(
            df_mes["Total Disp"].sum()
        )

        dias_trabajados_mes = int(
            df_mes["Trabajado"].sum()
        )

        c1, c2 = st.columns(2)

        with c1:
            mostrar_tarjeta_resumen(
                "⬆️ Ingresos acumulados",
                ingresos_mes,
            )

        with c2:
            mostrar_tarjeta_resumen(
                "⬇️ Gastos acumulados",
                gastos_mes,
            )

        c1, c2 = st.columns(2)

        with c1:
            mostrar_tarjeta_resumen(
                "📈 Ganancia estimada",
                ganancia_mes,
            )

        with c2:
            mostrar_tarjeta_resumen(
                "💵 Disponible acumulado",
                disponible_mes,
                ayuda=(
                    "Suma de los valores diarios de Total Disp "
                    "durante el mes."
                ),
            )

        c1, c2 = st.columns(2)

        with c1:
            st.metric(
                "🚗 Días trabajados",
                dias_trabajados_mes,
            )

        with c2:
            promedio_disponible_mes = (
                disponible_mes / dias_trabajados_mes
                if dias_trabajados_mes > 0
                else 0
            )

            mostrar_tarjeta_resumen(
                "Promedio disponible diario",
                promedio_disponible_mes,
            )

    else:
        st.info(
            f"Todavía no hay registros para {nombre_mes(mes_actual)}."
        )

    # -----------------------------------------------------
    # 4. ANÁLISIS DEL PERÍODO
    # -----------------------------------------------------

    st.markdown("---")
    st.subheader("🔎 Análisis del período")

    st.caption(
        "Consulta los promedios y el rendimiento de las "
        "jornadas dentro de un período específico."
    )

    tipo_filtro = st.radio(
        "Selecciona el período:",
        [
            "Por Mes",
            "Rango Personalizado",
        ],
        horizontal=True,
        key="inicio_tipo_filtro",
    )

    fecha_minima = df["Fecha"].min().date()
    fecha_maxima = df["Fecha"].max().date()

    if tipo_filtro == "Por Mes":

        meses_disponibles = sorted(
            df["AñoMes"].dropna().unique().tolist(),
            reverse=True,
        )

        mes_predeterminado = (
            mes_actual
            if mes_actual in meses_disponibles
            else meses_disponibles[0]
        )

        mes_seleccionado = st.selectbox(
            "Mes:",
            options=meses_disponibles,
            index=meses_disponibles.index(
                mes_predeterminado
            ),
            format_func=nombre_mes,
            key="inicio_mes",
        )

        df_periodo = df[
            df["AñoMes"] == mes_seleccionado
        ].copy()

        titulo_periodo = nombre_mes(
            mes_seleccionado
        )

    else:

        c1, c2 = st.columns(2)

        with c1:
            fecha_inicio = st.date_input(
                "Desde:",
                value=fecha_minima,
                min_value=fecha_minima,
                max_value=fecha_maxima,
                key="inicio_fecha_inicio",
            )

        with c2:
            fecha_fin = st.date_input(
                "Hasta:",
                value=fecha_maxima,
                min_value=fecha_minima,
                max_value=fecha_maxima,
                key="inicio_fecha_fin",
            )

        if fecha_inicio > fecha_fin:
            st.warning(
                "La fecha inicial no puede ser posterior "
                "a la fecha final."
            )
            return

        df_periodo = df[
            (df["Fecha"].dt.date >= fecha_inicio)
            & (df["Fecha"].dt.date <= fecha_fin)
        ].copy()

        titulo_periodo = (
            f"{fecha_inicio.strftime('%d/%m/%Y')} "
            f"al {fecha_fin.strftime('%d/%m/%Y')}"
        )

    if df_periodo.empty:
        st.info(
            "No hay registros para el período seleccionado."
        )
        return

    df_periodo = est.preparar(df_periodo)

    resumen = est.resumen_periodo(
        df_periodo
    )

    dias_trabajados = int(
        df_periodo["Trabajado"].sum()
    )

    promedio_ingresos = (
        resumen["ingresos"] / dias_trabajados
        if dias_trabajados > 0
        else 0
    )

    promedio_disponible = (
        resumen["disponible"] / dias_trabajados
        if dias_trabajados > 0
        else 0
    )

    st.caption(
        f"Resultados correspondientes a {titulo_periodo}."
    )

    # Indicadores del período.

    c1, c2 = st.columns(2)

    with c1:
        mostrar_tarjeta_resumen(
            "Promedio de ingresos diario",
            promedio_ingresos,
        )

    with c2:
        mostrar_tarjeta_resumen(
            "Promedio disponible diario",
            promedio_disponible,
        )

    st.metric(
        "🚗 Días trabajados",
        dias_trabajados,
    )

    # Mejores y peores jornadas.

    mejor_dia = resumen["mejor_dia"]
    peor_dia = resumen["peor_dia"]

    if mejor_dia is not None or peor_dia is not None:

        c1, c2 = st.columns(2)

        with c1:
            if mejor_dia is not None:
                st.markdown(
                    "**🏆 Día con mayor ganancia**"
                )

                st.write(
                    fecha_formateada(
                        mejor_dia["Fecha"]
                    )
                )

                st.write(
                    pesos(
                        obtener_valor(
                            mejor_dia,
                            "Ganancia Est",
                        )
                    )
                )

        with c2:
            if peor_dia is not None:
                st.markdown(
                    "**📉 Día con menor ganancia**"
                )

                st.write(
                    fecha_formateada(
                        peor_dia["Fecha"]
                    )
                )

                st.write(
                    pesos(
                        obtener_valor(
                            peor_dia,
                            "Ganancia Est",
                        )
                    )
                )

    else:
        st.info(
            "No hay jornadas trabajadas en este período."
        )

    # -----------------------------------------------------
    # 5. EXPORTACIÓN A EXCEL
    # -----------------------------------------------------

    st.markdown("---")

    with st.expander("📥 Exportar registros a Excel"):

        st.write(
            "Descarga los registros correspondientes al "
            "período seleccionado en el análisis."
        )

        archivo_excel = convertir_df_a_excel(
            df_periodo
        )

        if archivo_excel is not None:

            nombre_archivo = (
                f"Control_Financiero_{titulo_periodo}"
                .replace(" ", "_")
                .replace("/", "-")
            )

            st.download_button(
                label="📊 Descargar reporte en Excel",
                data=archivo_excel,
                file_name=f"{nombre_archivo}.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                use_container_width=True,
            )

    # -----------------------------------------------------
    # 6. ACCESO A LAS DEMÁS FUNCIONES
    # -----------------------------------------------------

    st.markdown("---")

    st.caption(
        "Utiliza el menú superior para registrar nuevos días, "
        "importar información o consultar el análisis financiero completo."
    )
