from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Estimación de peso por calibre",
    page_icon="🫐",
    layout="wide",
)

ARCHIVO_EXCEL = Path(__file__).parent / "data" / "Historico_Calibres_Peso.xlsx"
HOJA_EXCEL = "Hoja1"

COLUMNA_VARIEDAD = "variety"
COLUMNA_CALIBRE = "Calibre Promedio"
COLUMNA_PESO = "Peso Promedio"


@st.cache_data(show_spinner=False)
def cargar_datos(ruta: Path) -> pd.DataFrame:
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {ruta}")

    df = pd.read_excel(ruta, sheet_name=HOJA_EXCEL)
    requeridas = {COLUMNA_VARIEDAD, COLUMNA_CALIBRE, COLUMNA_PESO}
    faltantes = requeridas.difference(df.columns)
    if faltantes:
        raise ValueError("Faltan columnas: " + ", ".join(sorted(faltantes)))

    df = df[[COLUMNA_VARIEDAD, COLUMNA_CALIBRE, COLUMNA_PESO]].copy()
    df[COLUMNA_VARIEDAD] = df[COLUMNA_VARIEDAD].astype("string").str.strip().str.upper()
    df[COLUMNA_CALIBRE] = pd.to_numeric(df[COLUMNA_CALIBRE], errors="coerce")
    df[COLUMNA_PESO] = pd.to_numeric(df[COLUMNA_PESO], errors="coerce")
    df = df.dropna(subset=[COLUMNA_VARIEDAD, COLUMNA_CALIBRE, COLUMNA_PESO])
    return df[(df[COLUMNA_CALIBRE] > 0) & (df[COLUMNA_PESO] > 0)]


def metricas(y_real: np.ndarray, y_estimado: np.ndarray) -> dict:
    residuos = y_real - y_estimado
    ss_res = np.sum(residuos ** 2)
    ss_tot = np.sum((y_real - np.mean(y_real)) ** 2)
    return {
        "R2": float(1 - ss_res / ss_tot) if ss_tot > 0 else np.nan,
        "MAE": float(np.mean(np.abs(residuos))),
        "RMSE": float(np.sqrt(np.mean(residuos ** 2))),
    }


def ajustar_modelos(datos_variedad: pd.DataFrame) -> dict:
    x = datos_variedad[COLUMNA_CALIBRE].to_numpy(dtype=float)
    y = datos_variedad[COLUMNA_PESO].to_numpy(dtype=float)
    if len(x) < 3:
        raise ValueError("Registros insuficientes")

    pendiente, intercepto = np.polyfit(x, y, 1)
    pred_lineal = intercepto + pendiente * x
    met_lineal = metricas(y, pred_lineal)

    exponente, log_coeficiente = np.polyfit(np.log(x), np.log(y), 1)
    coeficiente = np.exp(log_coeficiente)
    pred_potencial = coeficiente * np.power(x, exponente)
    met_potencial = metricas(y, pred_potencial)

    return {
        "lineal": {"intercepto": float(intercepto), "pendiente": float(pendiente), **met_lineal},
        "potencial": {"coeficiente": float(coeficiente), "exponente": float(exponente), **met_potencial},
        "mejor_modelo": "Lineal" if met_lineal["RMSE"] <= met_potencial["RMSE"] else "Potencial",
        "calibre_min": float(np.min(x)),
        "calibre_max": float(np.max(x)),
        "registros": int(len(x)),
    }


def calcular_peso(calibre: float, modelo: str, parametros: dict) -> float:
    if modelo == "Lineal":
        return parametros["lineal"]["intercepto"] + parametros["lineal"]["pendiente"] * calibre
    return parametros["potencial"]["coeficiente"] * calibre ** parametros["potencial"]["exponente"]


def formato_formula(modelo: str, parametros: dict) -> str:
    if modelo == "Lineal":
        a = parametros["lineal"]["intercepto"]
        b = parametros["lineal"]["pendiente"]
        signo = "+" if b >= 0 else "-"
        return f"Peso = {a:.4f} {signo} {abs(b):.4f} × Calibre"
    c = parametros["potencial"]["coeficiente"]
    d = parametros["potencial"]["exponente"]
    return f"Peso = {c:.6f} × Calibre^{d:.4f}"


@st.cache_data(show_spinner=False)
def calcular_parametros_por_variedad(datos: pd.DataFrame) -> dict:
    modelos = {}
    for variedad, grupo in datos.groupby(COLUMNA_VARIEDAD):
        try:
            modelos[variedad] = ajustar_modelos(grupo)
        except Exception:
            pass
    return modelos


def modelo_aplicado(opcion: str, parametros: dict) -> str:
    return parametros["mejor_modelo"] if opcion == "Mejor modelo" else opcion


try:
    datos = cargar_datos(ARCHIVO_EXCEL)
except Exception as error:
    st.error(str(error))
    st.stop()

modelos = calcular_parametros_por_variedad(datos)
if not modelos:
    st.error("No se pudieron calcular modelos por variedad.")
    st.stop()

st.title("🫐 Estimación de peso por calibre")
st.caption("Consulta individual, cuadro de doble entrada y curvas estimadas por variedad.")

with st.sidebar:
    st.header("Configuración")
    if st.button("Actualizar información"):
        st.cache_data.clear()
        st.rerun()
    modelo_global = st.selectbox("Modelo para tabla y gráficos", ["Mejor modelo", "Lineal", "Potencial"])

st.subheader("Consulta individual")
c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    variedad = st.selectbox("Variedad", sorted(modelos.keys()))
with c2:
    calibre = st.number_input("Calibre", min_value=0.01, value=17.0, step=0.1, format="%.2f")
with c3:
    opcion_modelo = st.selectbox("Modelo", ["Mejor modelo", "Lineal", "Potencial"], key="individual")

parametros = modelos[variedad]
modelo_individual = modelo_aplicado(opcion_modelo, parametros)
peso = calcular_peso(calibre, modelo_individual, parametros)

r1, r2 = st.columns([1, 2])
with r1:
    st.metric(f"Peso estimado — {modelo_individual}", f"{peso:.3f} g")
with r2:
    st.info(formato_formula(modelo_individual, parametros))

st.divider()
st.subheader("Cuadro de doble entrada")

m1, m2, m3 = st.columns(3)
with m1:
    calibre_inicio = st.number_input("Calibre inicial", min_value=0.1, value=12.0, step=0.5)
with m2:
    calibre_fin = st.number_input("Calibre final", min_value=0.1, value=22.0, step=0.5)
with m3:
    intervalo = st.number_input("Intervalo", min_value=0.1, value=1.0, step=0.1)

if calibre_fin <= calibre_inicio:
    st.error("El calibre final debe ser mayor que el calibre inicial.")
    st.stop()

calibres = np.arange(calibre_inicio, calibre_fin + intervalo / 2, intervalo).round(2).tolist()
filas = []
for nombre_variedad, par in modelos.items():
    modelo = modelo_aplicado(modelo_global, par)
    fila = {"Variedad": nombre_variedad}
    for c in calibres:
        fila[f"{c:.1f} mm"] = calcular_peso(c, modelo, par)
    filas.append(fila)

tabla = pd.DataFrame(filas).set_index("Variedad").sort_index()
st.dataframe(tabla.style.format("{:.3f}"), use_container_width=True, height=min(750, 80 + 35 * len(tabla)))

st.download_button(
    "Descargar cuadro en CSV",
    tabla.reset_index().to_csv(index=False).encode("utf-8-sig"),
    "matriz_peso_variedad_calibre.csv",
    "text/csv",
)

st.divider()
st.subheader("Gráficos de líneas")

seleccionadas = st.multiselect(
    "Variedades a mostrar",
    options=sorted(modelos.keys()),
    default=sorted(modelos.keys())[:5],
)

if seleccionadas:
    registros = []
    for nombre_variedad in seleccionadas:
        par = modelos[nombre_variedad]
        modelo = modelo_aplicado(modelo_global, par)
        for c in calibres:
            registros.append({
                "Calibre": c,
                "Variedad": nombre_variedad,
                "Peso estimado": calcular_peso(c, modelo, par),
            })

    df_grafico = pd.DataFrame(registros)
    pivote = df_grafico.pivot(index="Calibre", columns="Variedad", values="Peso estimado")
    st.line_chart(pivote, use_container_width=True, x_label="Calibre (mm)", y_label="Peso estimado (g)")
else:
    st.info("Selecciona al menos una variedad.")

with st.expander("Ver fórmulas y métricas por variedad"):
    resumen = []
    for nombre_variedad, par in modelos.items():
        resumen.append({
            "Variedad": nombre_variedad,
            "Modelo recomendado": par["mejor_modelo"],
            "Fórmula lineal": formato_formula("Lineal", par),
            "R² lineal": par["lineal"]["R2"],
            "RMSE lineal": par["lineal"]["RMSE"],
            "Fórmula potencial": formato_formula("Potencial", par),
            "R² potencial": par["potencial"]["R2"],
            "RMSE potencial": par["potencial"]["RMSE"],
        })
    st.dataframe(pd.DataFrame(resumen), use_container_width=True, hide_index=True)
