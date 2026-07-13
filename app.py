from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st


# ============================================================
# CONFIGURACIÓN
# ============================================================
st.set_page_config(
    page_title="Calculadora de peso por calibre",
    page_icon="🫐",
    layout="centered",
)

ARCHIVO_EXCEL = Path(__file__).parent / "data" / "Historico_Calibres_Peso.xlsx"
HOJA_EXCEL = "Hoja1"

COLUMNA_VARIEDAD = "variety"
COLUMNA_CALIBRE = "Calibre Promedio"
COLUMNA_PESO = "Peso Promedio"


# ============================================================
# FUNCIONES
# ============================================================
@st.cache_data(show_spinner=False)
def cargar_datos(ruta: Path) -> pd.DataFrame:
    if not ruta.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo: {ruta}. "
            "Verifica que esté dentro de la carpeta data."
        )

    df = pd.read_excel(ruta, sheet_name=HOJA_EXCEL)

    columnas_requeridas = {
        COLUMNA_VARIEDAD,
        COLUMNA_CALIBRE,
        COLUMNA_PESO,
    }

    faltantes = columnas_requeridas.difference(df.columns)
    if faltantes:
        raise ValueError(
            "Faltan columnas obligatorias en el Excel: "
            + ", ".join(sorted(faltantes))
        )

    df = df[
        [COLUMNA_VARIEDAD, COLUMNA_CALIBRE, COLUMNA_PESO]
    ].copy()

    df[COLUMNA_VARIEDAD] = (
        df[COLUMNA_VARIEDAD]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    df[COLUMNA_CALIBRE] = pd.to_numeric(
        df[COLUMNA_CALIBRE], errors="coerce"
    )
    df[COLUMNA_PESO] = pd.to_numeric(
        df[COLUMNA_PESO], errors="coerce"
    )

    df = df.dropna(
        subset=[COLUMNA_VARIEDAD, COLUMNA_CALIBRE, COLUMNA_PESO]
    )

    # Se excluyen valores no válidos para los modelos.
    df = df[
        (df[COLUMNA_CALIBRE] > 0)
        & (df[COLUMNA_PESO] > 0)
    ]

    return df


def metricas(y_real: np.ndarray, y_estimado: np.ndarray) -> dict:
    residuos = y_real - y_estimado
    ss_res = np.sum(residuos ** 2)
    ss_tot = np.sum((y_real - np.mean(y_real)) ** 2)

    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else np.nan
    mae = np.mean(np.abs(residuos))
    rmse = np.sqrt(np.mean(residuos ** 2))

    return {
        "R2": float(r2),
        "MAE": float(mae),
        "RMSE": float(rmse),
    }


def ajustar_modelos(datos_variedad: pd.DataFrame) -> dict:
    x = datos_variedad[COLUMNA_CALIBRE].to_numpy(dtype=float)
    y = datos_variedad[COLUMNA_PESO].to_numpy(dtype=float)

    if len(x) < 3:
        raise ValueError(
            "La variedad seleccionada no tiene suficientes registros "
            "para ajustar los modelos."
        )

    # Modelo lineal: Peso = intercepto + pendiente × Calibre
    pendiente, intercepto = np.polyfit(x, y, 1)
    pred_lineal = intercepto + pendiente * x
    met_lineal = metricas(y, pred_lineal)

    # Modelo potencial: Peso = coeficiente × Calibre ^ exponente
    # ln(Peso) = ln(coeficiente) + exponente × ln(Calibre)
    log_x = np.log(x)
    log_y = np.log(y)
    exponente, log_coeficiente = np.polyfit(log_x, log_y, 1)
    coeficiente = np.exp(log_coeficiente)
    pred_potencial = coeficiente * np.power(x, exponente)
    met_potencial = metricas(y, pred_potencial)

    mejor_modelo = (
        "Lineal"
        if met_lineal["RMSE"] <= met_potencial["RMSE"]
        else "Potencial"
    )

    return {
        "lineal": {
            "intercepto": float(intercepto),
            "pendiente": float(pendiente),
            **met_lineal,
        },
        "potencial": {
            "coeficiente": float(coeficiente),
            "exponente": float(exponente),
            **met_potencial,
        },
        "mejor_modelo": mejor_modelo,
        "calibre_min": float(np.min(x)),
        "calibre_max": float(np.max(x)),
        "registros": int(len(x)),
    }


def calcular_peso(calibre: float, modelo: str, parametros: dict) -> float:
    if modelo == "Lineal":
        return (
            parametros["lineal"]["intercepto"]
            + parametros["lineal"]["pendiente"] * calibre
        )

    return (
        parametros["potencial"]["coeficiente"]
        * calibre ** parametros["potencial"]["exponente"]
    )


def formato_formula(modelo: str, parametros: dict) -> str:
    if modelo == "Lineal":
        a = parametros["lineal"]["intercepto"]
        b = parametros["lineal"]["pendiente"]
        signo = "+" if b >= 0 else "-"
        return f"Peso = {a:.4f} {signo} {abs(b):.4f} × Calibre"

    c = parametros["potencial"]["coeficiente"]
    d = parametros["potencial"]["exponente"]
    return f"Peso = {c:.6f} × Calibre^{d:.4f}"


# ============================================================
# INTERFAZ
# ============================================================
st.title("🫐 Calculadora de peso por calibre")
st.caption(
    "Las fórmulas se calculan automáticamente para cada variedad "
    "utilizando el histórico de calibres y pesos."
)

try:
    datos = cargar_datos(ARCHIVO_EXCEL)
except Exception as error:
    st.error(str(error))
    st.stop()

variedades = sorted(datos[COLUMNA_VARIEDAD].dropna().unique().tolist())

if not variedades:
    st.error("No se encontraron variedades válidas en el archivo Excel.")
    st.stop()

variedad = st.selectbox(
    "Variedad",
    options=variedades,
)

datos_variedad = datos[
    datos[COLUMNA_VARIEDAD] == variedad
].copy()

try:
    parametros = ajustar_modelos(datos_variedad)
except Exception as error:
    st.error(str(error))
    st.stop()

col1, col2 = st.columns(2)

with col1:
    calibre = st.number_input(
        "Calibre",
        min_value=0.01,
        value=17.00,
        step=0.10,
        format="%.2f",
    )

with col2:
    modelo = st.selectbox(
        "Modelo",
        options=["Mejor modelo", "Lineal", "Potencial"],
    )

modelo_aplicado = (
    parametros["mejor_modelo"]
    if modelo == "Mejor modelo"
    else modelo
)

peso_estimado = calcular_peso(
    calibre=calibre,
    modelo=modelo_aplicado,
    parametros=parametros,
)

st.metric(
    label=f"Peso estimado — modelo {modelo_aplicado}",
    value=f"{peso_estimado:.3f} g",
)

st.info(formato_formula(modelo_aplicado, parametros))

if not (
    parametros["calibre_min"]
    <= calibre
    <= parametros["calibre_max"]
):
    st.warning(
        "El calibre ingresado está fuera del rango histórico de esta "
        f"variedad ({parametros['calibre_min']:.2f} a "
        f"{parametros['calibre_max']:.2f}). El resultado es una "
        "extrapolación y puede ser menos confiable."
    )

with st.expander("Ver detalle del modelo"):
    st.write(f"**Variedad:** {variedad}")
    st.write(f"**Registros utilizados:** {parametros['registros']}")
    st.write(
        f"**Rango histórico de calibre:** "
        f"{parametros['calibre_min']:.2f} – "
        f"{parametros['calibre_max']:.2f}"
    )
    st.write(f"**Modelo recomendado:** {parametros['mejor_modelo']}")

    resumen = pd.DataFrame(
        [
            {
                "Modelo": "Lineal",
                "Fórmula": formato_formula("Lineal", parametros),
                "R²": parametros["lineal"]["R2"],
                "MAE": parametros["lineal"]["MAE"],
                "RMSE": parametros["lineal"]["RMSE"],
            },
            {
                "Modelo": "Potencial",
                "Fórmula": formato_formula("Potencial", parametros),
                "R²": parametros["potencial"]["R2"],
                "MAE": parametros["potencial"]["MAE"],
                "RMSE": parametros["potencial"]["RMSE"],
            },
        ]
    )

    st.dataframe(
        resumen.style.format(
            {
                "R²": "{:.4f}",
                "MAE": "{:.4f}",
                "RMSE": "{:.4f}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

with st.expander("Calcular varios calibres"):
    texto_calibres = st.text_area(
        "Ingresa calibres separados por coma",
        placeholder="Ejemplo: 14, 15.5, 17, 18.2",
    )

    if st.button("Calcular tabla"):
        try:
            lista_calibres = [
                float(valor.strip())
                for valor in texto_calibres.replace(";", ",").split(",")
                if valor.strip()
            ]

            if not lista_calibres:
                raise ValueError("Ingresa al menos un calibre.")

            resultado = pd.DataFrame(
                {
                    "Variedad": variedad,
                    "Calibre": lista_calibres,
                    "Modelo": modelo_aplicado,
                    "Peso estimado (g)": [
                        calcular_peso(
                            valor,
                            modelo_aplicado,
                            parametros,
                        )
                        for valor in lista_calibres
                    ],
                }
            )

            st.dataframe(
                resultado.style.format(
                    {
                        "Calibre": "{:.2f}",
                        "Peso estimado (g)": "{:.3f}",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

            st.download_button(
                "Descargar resultados en CSV",
                data=resultado.to_csv(index=False).encode("utf-8-sig"),
                file_name="pesos_estimados.csv",
                mime="text/csv",
            )

        except ValueError as error:
            st.error(f"Revisa los calibres ingresados: {error}")
