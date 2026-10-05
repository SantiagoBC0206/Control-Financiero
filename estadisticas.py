"""
estadisticas.py — Cálculos de resumen (día, mes, año). Solo usa pandas.

Trabaja sobre el DataFrame que devuelve db.resumen_dias().
Un día cuenta como "trabajado" si tuvo ingresos (> 0).
"""

import pandas as pd


def preparar(df):
    """Agrega columnas auxiliares: fecha real, si fue trabajado y año-mes."""
    df = df.copy()
    df["Fecha"] = pd.to_datetime(df["Fecha"])
    df["Trabajado"] = df["Total Ingresos"] > 0
    df["AñoMes"] = df["Fecha"].dt.strftime("%Y-%m")
    return df


def grupos_columnas(df):
    """Devuelve (columnas_ingresos, columnas_gastos, columnas_movimientos)."""
    cols = list(df.columns)
    i_ing = cols.index("Total Ingresos")
    i_gas = cols.index("Total Gastos")
    i_gan = cols.index("Ganancia Est")
    i_disp = cols.index("Total Disp")
    return cols[1:i_ing], cols[i_ing + 1:i_gas], cols[i_gan + 1:i_disp]


def resumen_periodo(df):
    """Totales y datos destacados de un conjunto de días (un mes, un año...)."""
    ing, gas, _ = grupos_columnas(df)
    trabajados = df[df["Trabajado"]]
    dias = len(trabajados)

    ganancia = int(df["Ganancia Est"].sum())
    resultado = {
        "ingresos": int(df["Total Ingresos"].sum()),
        "gastos": int(df["Total Gastos"].sum()),
        "ganancia": ganancia,
        "disponible": int(df["Total Disp"].sum()),
        "diferencia": int(df["Diferencia"].sum()),
        "dias_trabajados": dias,
        "promedio_dia": ganancia / dias if dias else 0,
        "mejor_dia": None,
        "peor_dia": None,
        "por_plataforma": df[ing].sum(),
        "por_categoria": df[gas].sum(),
    }
    if dias:
        mejor = trabajados.loc[trabajados["Ganancia Est"].idxmax()]
        peor = trabajados.loc[trabajados["Ganancia Est"].idxmin()]
        resultado["mejor_dia"] = (mejor["Fecha"], int(mejor["Ganancia Est"]))
        resultado["peor_dia"] = (peor["Fecha"], int(peor["Ganancia Est"]))
    return resultado


def resumen_por_mes(df):
    """Una fila por mes (ordenado) con ingresos, gastos, ganancia y días trabajados."""
    por_mes = df.groupby("AñoMes").agg(
        Ingresos=("Total Ingresos", "sum"),
        Gastos=("Total Gastos", "sum"),
        Ganancia=("Ganancia Est", "sum"),
        Dias=("Trabajado", "sum"),
    )
    por_mes["Dias"] = por_mes["Dias"].astype(int)
    por_mes["Promedio"] = (por_mes["Ganancia"] / por_mes["Dias"].where(por_mes["Dias"] > 0)).fillna(0)
    return por_mes.sort_index()


def dia_anterior_trabajado(df, fecha):
    """Último día trabajado antes de 'fecha'. Devuelve la fila o None."""
    previos = df[(df["Fecha"] < pd.Timestamp(fecha)) & df["Trabajado"]]
    if previos.empty:
        return None
    return previos.sort_values("Fecha").iloc[-1]
