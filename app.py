"""
Screener personalizado — Acciones Argentinas (ADRs), Acciones EEUU,
Bitcoin, Commodities, Dólar MEP y Riesgo País
Autor: generado con Claude
"""

import streamlit as st
import yfinance as yf
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Screener Personalizado", layout="wide")

# ----------------------------------------------------------------------------
# CONFIG: universo de activos por default. Editá estas listas a gusto.
# ----------------------------------------------------------------------------

# GGAL, BMA, BBAR, YPF, VIST y CRESY cotizan como ADRs en NYSE/NASDAQ,
# así que se pueden traer directo de Yahoo Finance sin pasar por BYMA.
DEFAULT_AR_STOCKS = "GGAL, BMA, BBAR, YPF, VIST, CRESY"

# DJI es un índice (Dow Jones); en Yahoo Finance el ticker lleva el prefijo ^
DEFAULT_US_STOCKS = "SPY, ^DJI, QQQ"

DEFAULT_CRYPTO = "BTC-USD"

COMMODITY_TICKERS = {
    "BZ=F": "Brent (petróleo)",
    "GC=F": "Oro",
    "SI=F": "Plata",
    "LIT": "Litio (ETF Global X Lithium)",
    "ZS=F": "Soja",
    "ZW=F": "Trigo",
    "ZC=F": "Maíz",
}

MEP_API_URL = "https://dolarapi.com/v1/dolares/bolsa"
RIESGO_PAIS_API_URL = "https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais/ultimo"

# ----------------------------------------------------------------------------
# FUNCIONES DE DATOS
# ----------------------------------------------------------------------------

@st.cache_data(ttl=300)
def get_yf_data(tickers: list[str]) -> pd.DataFrame:
    """Trae ticker, nombre, precio y variación % vs cierre anterior.

    Usa siempre el histórico diario (Close) en vez de precios intradía,
    para que funcione igual con mercado abierto o cerrado: si el mercado
    está cerrado, 'Precio' es el último cierre disponible y 'Variación %'
    es la variación de esa última rueda vs la rueda anterior.
    """
    rows = []
    if not tickers:
        return pd.DataFrame(rows)

    for t in tickers:
        try:
            tk = yf.Ticker(t)
            hist = tk.history(period="5d")

            if hist.empty or len(hist) < 2:
                rows.append({"Ticker": t, "Nombre": t, "Precio": None, "Variación %": None})
                continue

            last_close = hist["Close"].iloc[-1]
            prev_close = hist["Close"].iloc[-2]

            try:
                name = tk.info.get("shortName", t)
            except Exception:
                name = t

            change_pct = (last_close / prev_close - 1) * 100
            rows.append({
                "Ticker": t,
                "Nombre": name,
                "Precio": round(float(last_close), 2),
                "Variación %": round(float(change_pct), 2),
            })
        except Exception as e:
            rows.append({"Ticker": t, "Nombre": f"Error: {e}", "Precio": None, "Variación %": None})

    return pd.DataFrame(rows)


@st.cache_data(ttl=300)
def get_mep() -> pd.DataFrame:
    """Trae el dólar MEP desde dolarapi.com (calculado como ratio AL30/AL30D)."""
    try:
        r = requests.get(MEP_API_URL, timeout=10)
        r.raise_for_status()
        d = r.json()
        precio = d.get("venta")
        return pd.DataFrame([{
            "Ticker": "MEP",
            "Nombre": "Dólar MEP (AL30/AL30D)",
            "Precio": precio,
            "Variación %": None,  # la API no da variación intradía directa
        }])
    except Exception as e:
        return pd.DataFrame([{
            "Ticker": "MEP",
            "Nombre": f"Error al obtener MEP: {e}",
            "Precio": None,
            "Variación %": None,
        }])


@st.cache_data(ttl=300)
def get_riesgo_pais() -> pd.DataFrame:
    """Trae el último valor de riesgo país (EMBI+ Argentina, JP Morgan)
    desde la API pública ArgentinaDatos."""
    try:
        r = requests.get(RIESGO_PAIS_API_URL, timeout=10)
        r.raise_for_status()
        d = r.json()
        valor = d.get("valor")
        fecha = d.get("fecha", "")
        return pd.DataFrame([{
            "Ticker": "RP",
            "Nombre": f"Riesgo País Argentina (EMBI+) — {fecha}",
            "Precio": valor,
            "Variación %": None,
        }])
    except Exception as e:
        return pd.DataFrame([{
            "Ticker": "RP",
            "Nombre": f"Error al obtener riesgo país: {e}",
            "Precio": None,
            "Variación %": None,
        }])


def color_variacion(val):
    if val is None or pd.isna(val):
        return ""
    color = "#1a7f37" if val >= 0 else "#c0392b"
    return f"color: {color}; font-weight: 600;"


def style_table(df: pd.DataFrame):
    """Aplica color condicional a la columna Variación %, compatible con
    pandas viejo (applymap) y nuevo (map, ya que applymap fue removido)."""
    styler = df.style
    try:
        return styler.map(color_variacion, subset=["Variación %"])
    except AttributeError:
        return styler.applymap(color_variacion, subset=["Variación %"])


# ----------------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------------

st.title("📊 Screener Personalizado")
st.caption(f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

with st.sidebar:
    st.header("Universo de activos")
    ar_input = st.text_area("Acciones Argentinas / ADRs (tickers separados por coma)", DEFAULT_AR_STOCKS)
    us_input = st.text_area("Acciones / índices EE.UU. (tickers separados por coma)", DEFAULT_US_STOCKS)
    crypto_input = st.text_area("Cripto (tickers separados por coma)", DEFAULT_CRYPTO)
    show_commodities = st.checkbox("Mostrar commodities", value=True)
    show_mep = st.checkbox("Mostrar Dólar MEP", value=True)
    show_riesgo_pais = st.checkbox("Mostrar Riesgo País", value=True)
    if st.button("🔄 Refrescar datos"):
        st.cache_data.clear()

ar_tickers = [t.strip().upper() for t in ar_input.split(",") if t.strip()]
us_tickers = [t.strip().upper() for t in us_input.split(",") if t.strip()]
crypto_tickers = [t.strip().upper() for t in crypto_input.split(",") if t.strip()]

if show_mep or show_riesgo_pais:
    st.subheader("Tipo de Cambio y Riesgo País")
    frames = []
    if show_mep:
        frames.append(get_mep())
    if show_riesgo_pais:
        frames.append(get_riesgo_pais())
    st.dataframe(pd.concat(frames, ignore_index=True), use_container_width=True, hide_index=True)

if ar_tickers:
    st.subheader("Acciones Argentinas (ADRs)")
    df_ar = get_yf_data(ar_tickers)
    st.dataframe(style_table(df_ar), use_container_width=True, hide_index=True)

if us_tickers:
    st.subheader("Acciones / Índices EE.UU.")
    df_us = get_yf_data(us_tickers)
    st.dataframe(style_table(df_us), use_container_width=True, hide_index=True)

if crypto_tickers:
    st.subheader("Bitcoin / Cripto")
    df_crypto = get_yf_data(crypto_tickers)
    st.dataframe(style_table(df_crypto), use_container_width=True, hide_index=True)

if show_commodities:
    st.subheader("Commodities")
    df_comm = get_yf_data(list(COMMODITY_TICKERS.keys()))
    df_comm["Nombre"] = df_comm["Ticker"].map(COMMODITY_TICKERS)
    st.dataframe(style_table(df_comm), use_container_width=True, hide_index=True)

st.divider()
st.caption(
    "Fuentes: Yahoo Finance (acciones, ADRs, índices, cripto, commodities) vía yfinance · "
    "dolarapi.com (Dólar MEP, calculado como AL30/AL30D) · "
    "ArgentinaDatos API (Riesgo País, EMBI+ de JP Morgan). "
    "Precio y Variación % siempre reflejan la última rueda con cierre disponible "
    "(si el mercado está cerrado, se muestra el último cierre y su variación vs la rueda anterior). "
    "GGAL, BMA, BBAR, YPF, VIST y CRESY se muestran como ADRs (cotizan en NYSE/NASDAQ en USD), "
    "no como sus equivalentes en pesos de BYMA."
)
