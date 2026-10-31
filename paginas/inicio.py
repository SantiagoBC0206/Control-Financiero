
import io

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
            df_export["Fecha"], errors="coerce"
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
        df_export.columns, start=1
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
            registro, start=1
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
        df_export.columns, start=1
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
        df_export.columns, start=1
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
        df_export.columns, start=1
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
# FUNCIONES AUXILIARES DEL DASHBOARD
# =========================================================

def obtener_valor(registro, columna):
    """
    Obtiene un valor numérico de un registro.
    """
    if registro is None or columna not in registro.index:
        return 0

    valor = pd.to_numeric(
        registro[columna],
        errors="coerce",
    )

    return 0 if pd.isna(valor) else float(valor)


def fecha_formateada(valor):
    """
    Convierte una fecha en formato legible.
    """
    if valor is None or pd.isna(valor):
        return "Sin información"

    return pd.to_datetime(valor).strftime("%d/%m/%Y")


def grafico_vacio(mensaje):
    st.info(mensaje)


# =========================================================
# DASHBOARD PRINCIPAL
# =========================================================

def mostrar():

    st.subheader("📊 Dashboard Financiero")

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
            "el dashboard."
        )
        return

    df = est.preparar(df_original)

    if df.empty:
        st.info("No hay registros válidos para mostrar.")
        return

    # -----------------------------------------------------
    # 2. FILTROS
    # -----------------------------------------------------

    st.markdown("### 🔎 Consultar información")

    tipo_filtro = st.radio(
        "Selecciona el período que deseas consultar:",
        [
            "Por Mes",
            "Rango Personalizado",
        ],
        horizontal=True,
        key="dashboard_tipo_filtro",
    )

    fecha_minima = df["Fecha"].min().date()
    fecha_maxima = df["Fecha"].max().date()

    if tipo_filtro == "Por Mes":

        meses_disponibles = sorted(
            df["AñoMes"].dropna().unique().tolist(),
            reverse=True,
        )

        mes_actual = hoy().strftime("%Y-%m")

        mes_predeterminado = (
            mes_actual
            if mes_actual in meses_disponibles
            else meses_disponibles[0]
        )

        mes_seleccionado = st.selectbox(
            "Selecciona el mes:",
            options=meses_disponibles,
            index=meses_disponibles.index(
                mes_predeterminado
            ),
            format_func=nombre_mes,
            key="dashboard_mes",
        )

        df_filtrado = df[
            df["AñoMes"] == mes_seleccionado
        ].copy()

        titulo_periodo = nombre_mes(
            mes_seleccionado
        )

    else:

        columna1, columna2 = st.columns(2)

        with columna1:
            fecha_inicio = st.date_input(
                "Fecha inicial",
                value=fecha_minima,
                min_value=fecha_minima,
                max_value=fecha_maxima,
                key="dashboard_fecha_inicio",
            )

        with columna2:
            fecha_fin = st.date_input(
                "Fecha final",
                value=fecha_maxima,
                min_value=fecha_minima,
                max_value=fecha_maxima,
                key="dashboard_fecha_fin",
            )

        if fecha_inicio > fecha_fin:
            st.warning(
                "La fecha inicial no puede ser posterior "
                "a la fecha final."
            )
            return

        df_filtrado = df[
            (df["Fecha"].dt.date >= fecha_inicio)
            & (df["Fecha"].dt.date <= fecha_fin)
        ].copy()

        titulo_periodo = (
            f"{fecha_inicio.strftime('%d/%m/%Y')} "
            f"al {fecha_fin.strftime('%d/%m/%Y')}"
        )

    if df_filtrado.empty:
        st.warning(
            "No existen registros para el período seleccionado."
        )
        return

    df_filtrado = est.preparar(df_filtrado)

    # -----------------------------------------------------
    # 3. RESUMEN DEL PERÍODO
    # -----------------------------------------------------

    resumen = est.resumen_periodo(
        df_filtrado
    )

    ultimo_registro = resumen["ultimo_registro"]

    efectivo_final = obtener_valor(
        ultimo_registro,
        "Efectivo",
    )

    nequi_final = obtener_valor(
        ultimo_registro,
        "Nequi",
    )

    total_dias_trabajados = int(
        df_filtrado["Trabajado"].sum()
    )

    # Promedio de ingresos por día trabajado.
    promedio_ingresos = (
        resumen["ingresos"] / total_dias_trabajados
        if total_dias_trabajados > 0
        else 0
    )

    # Promedio disponible:
    # suma del total disponible / días trabajados.
    promedio_disponible = (
        resumen["disponible"] / total_dias_trabajados
        if total_dias_trabajados > 0
        else 0
    )

    st.markdown("---")

    st.markdown(
        f"### 📅 Resumen de {titulo_periodo}"
    )

    st.caption(
        f"Registros incluidos: {len(df_filtrado)} días. "
        f"Días trabajados: {total_dias_trabajados}."
    )

    # -----------------------------------------------------
    # 4. INDICADORES PRINCIPALES
    # -----------------------------------------------------

    st.markdown("#### Indicadores financieros")

    c1, c2 = st.columns(2)

    with c1:
        st.metric(
            "💰 Total disponible acumulado",
            pesos(resumen["disponible"]),
        )

    with c2:
        st.metric(
            "📈 Ganancia estimada",
            pesos(resumen["ganancia"]),
        )

    c3, c4 = st.columns(2)

    with c3:
        st.metric(
            "⬆️ Total ingresos",
            pesos(resumen["ingresos"]),
        )

    with c4:
        st.metric(
            "⬇️ Total gastos",
            pesos(resumen["gastos"]),
        )

    st.caption(
        "El total disponible corresponde a la suma de "
        "los valores diarios de Total Disp durante el período."
    )

    # -----------------------------------------------------
    # 5. SALDOS FINALES
    # -----------------------------------------------------

    fecha_ultimo_registro = fecha_formateada(
        ultimo_registro["Fecha"]
    )

    st.markdown("---")

    st.markdown(
        f"#### 💵 Saldos registrados al {fecha_ultimo_registro}"
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Efectivo",
            pesos(efectivo_final),
        )

    with c2:
        st.metric(
            "Nequi",
            pesos(nequi_final),
        )

    with c3:
        st.metric(
            "Total del último día",
            pesos(efectivo_final + nequi_final),
        )

    # -----------------------------------------------------
    # 6. INDICADORES COMPLEMENTARIOS
    # -----------------------------------------------------

    st.markdown("---")

    st.markdown("#### 📌 Análisis del período")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "Promedio de ingresos diario",
            pesos(promedio_ingresos),
        )

    with c2:
        st.metric(
            "Promedio disponible diario",
            pesos(promedio_disponible),
        )

    with c3:
        st.metric(
            "Días trabajados",
            total_dias_trabajados,
        )

    mejor_dia = resumen["mejor_dia"]
    peor_dia = resumen["peor_dia"]

    if mejor_dia is not None or peor_dia is not None:

        c1, c2 = st.columns(2)

        with c1:
            if mejor_dia is not None:
                st.markdown("**🏆 Día con mayor ganancia**")

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
                st.markdown("**📉 Día con menor ganancia**")

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

    # -----------------------------------------------------
    # 7. GRÁFICO DE INGRESOS Y GASTOS POR DÍA
    # -----------------------------------------------------

    st.markdown("---")

    st.markdown("### 📊 Actividad diaria")

    df_grafico = df_filtrado.copy()

    df_grafico["Día"] = (
        df_grafico["Fecha"].dt.strftime("%d/%m")
    )

    fig_diario = go.Figure()

    fig_diario.add_trace(
        go.Bar(
            x=df_grafico["Día"],
            y=df_grafico["Total Ingresos"],
            name="Ingresos",
        )
    )

    fig_diario.add_trace(
        go.Bar(
            x=df_grafico["Día"],
            y=df_grafico["Total Gastos"],
            name="Gastos",
        )
    )

    fig_diario.update_layout(
        title="Ingresos frente a gastos por día",
        xaxis_title="Día",
        yaxis_title="Valor en pesos",
        barmode="group",
        hovermode="x unified",
        legend_title="Concepto",
        margin=dict(
            l=10,
            r=10,
            t=50,
            b=10,
        ),
    )

    fig_diario.update_yaxes(
        tickprefix="$",
        separatethousands=True,
    )

    st.plotly_chart(
        fig_diario,
        use_container_width=True,
    )

    # -----------------------------------------------------
    # 8. DISTRIBUCIÓN DE INGRESOS Y GASTOS
    # -----------------------------------------------------

    st.markdown("---")

    st.markdown("### 🧾 Distribución financiera")

    col1, col2 = st.columns(2)

    with col1:

        st.markdown("**Ingresos por plataforma**")

        plataformas = resumen["por_plataforma"]

        datos_plataformas = {
            nombre: valor
            for nombre, valor in plataformas.items()
            if valor > 0
        }

        if datos_plataformas:

            fig_plataformas = px.pie(
                names=list(datos_plataformas.keys()),
                values=list(datos_plataformas.values()),
                hole=0.55,
            )

            fig_plataformas.update_traces(
                textposition="inside",
                textinfo="percent+label",
            )

            fig_plataformas.update_layout(
                showlegend=False,
                margin=dict(
                    l=5,
                    r=5,
                    t=20,
                    b=5,
                ),
            )

            st.plotly_chart(
                fig_plataformas,
                use_container_width=True,
            )

        else:
            grafico_vacio(
                "No hay ingresos registrados por plataforma."
            )

    with col2:

        st.markdown("**Gastos por categoría**")

        categorias = resumen["por_categoria"]

        datos_categorias = {
            nombre: valor
            for nombre, valor in categorias.items()
            if valor > 0
        }

        if datos_categorias:

            fig_gastos = px.pie(
                names=list(datos_categorias.keys()),
                values=list(datos_categorias.values()),
                hole=0.55,
            )

            fig_gastos.update_traces(
                textposition="inside",
                textinfo="percent+label",
            )

            fig_gastos.update_layout(
                showlegend=False,
                margin=dict(
                    l=5,
                    r=5,
                    t=20,
                    b=5,
                ),
            )

            st.plotly_chart(
                fig_gastos,
                use_container_width=True,
            )

        else:
            grafico_vacio(
                "No hay gastos registrados por categoría."
            )

    # -----------------------------------------------------
    # 9. COMPARACIÓN ENTRE MESES
    # -----------------------------------------------------

    st.markdown("---")

    st.markdown("### 📅 Comparación mensual")

    resumen_mensual = est.resumen_por_mes(df)

    if not resumen_mensual.empty:

        resumen_mensual = resumen_mensual.sort_values(
            "AñoMes"
        )

        datos_mensuales = resumen_mensual.melt(
            id_vars=["AñoMes"],
            value_vars=[
                "Ingresos",
                "Gastos",
            ],
            var_name="Concepto",
            value_name="Valor",
        )

        fig_mensual = px.bar(
            datos_mensuales,
            x="AñoMes",
            y="Valor",
            color="Concepto",
            barmode="group",
            title="Ingresos y gastos por mes",
        )

        fig_mensual.update_layout(
            xaxis_title="Mes",
            yaxis_title="Valor en pesos",
            hovermode="x unified",
            margin=dict(
                l=10,
                r=10,
                t=50,
                b=10,
            ),
        )

        fig_mensual.update_yaxes(
            tickprefix="$",
            separatethousands=True,
        )

        st.plotly_chart(
            fig_mensual,
            use_container_width=True,
        )

        st.markdown("**Resumen por mes**")

        tabla_mensual = resumen_mensual.copy()

        tabla_mensual["Mes"] = (
            tabla_mensual["AñoMes"].apply(nombre_mes)
        )

        tabla_mensual = tabla_mensual[
            [
                "Mes",
                "Ingresos",
                "Gastos",
                "Ganancia",
                "Disponible",
                "Dias",
            ]
        ]

        tabla_mensual = tabla_mensual.rename(
            columns={
                "Dias": "Días trabajados",
                "Disponible": "Disponible acumulado",
            }
        )

        st.dataframe(
            tabla_mensual,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Ingresos": st.column_config.NumberColumn(
                    format="$%d",
                ),
                "Gastos": st.column_config.NumberColumn(
                    format="$%d",
                ),
                "Ganancia": st.column_config.NumberColumn(
                    format="$%d",
                ),
                "Disponible acumulado": st.column_config.NumberColumn(
                    format="$%d",
                ),
            },
        )

    else:
        grafico_vacio(
            "Todavía no hay información suficiente "
            "para comparar meses."
        )

    # -----------------------------------------------------
    # 10. DESCARGAR REPORTE
    # -----------------------------------------------------

    st.markdown("---")

    st.markdown("### 📥 Exportar información")

    st.write(
        "Descarga los registros del período seleccionado "
        "en un archivo Excel."
    )

    archivo_excel = convertir_df_a_excel(
        df_filtrado
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
