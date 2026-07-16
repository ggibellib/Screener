"""
Screener personalizado — Acciones NYSE, ETFs, Commodities y Dólar MEP
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

DEFAULT_STOCKS = "AAPL, MSFT, JPM, XOM, KO, JNJ, GE, VST"
DEFAULT_ETFS = "SPY, QQQ, DIA, GLD, SLV"

COMMODITY_TICKERS = {
    "GC=F": "Oro (futuro COMEX)",
    "SI=F": "Plata (futuro COMEX)",
}

MEP_API_URL = "https://dolarapi.com/v1/dolares/bolsa"

# ----------------------------------------------------------------------------
# FUNCIONES DE DATOS
# ----------------------------------------------------------------------------

@st.cache_data(ttl=60)
def get_yf_data(tickers: list[str]) -> pd.DataFrame:
    """Trae ticker, nombre, precio actual y variación % vs cierre anterior."""
    rows = []
    if not tickers:
        return pd.DataFrame(rows)

    data = yf.Tickers(" ".join(tickers))
    for t in tickers:
        try:
            info = data.tickers[t].fast_info
            name = None
            try:
                name = data.tickers[t].info.get("shortName", t)
            except Exception:
                name = t

            price = info.get("last_price")
            prev_close = info.get("previous_close")

            if price is None or prev_close is None or prev_close == 0:
                rows.append({"Ticker": t, "Nombre": name, "Precio": None, "Variación %": None})
                continue

            change_pct = (price / prev_close - 1) * 100
            rows.append({
                "Ticker": t,
                "Nombre": name,
                "Precio": round(price, 2),
                "Variación %": round(change_pct, 2),
            })
        except Exception as e:
            rows.append({"Ticker": t, "Nombre": f"Error: {e}", "Precio": None, "Variación %": None})

    return pd.DataFrame(rows)


@st.cache_data(ttl=60)
def get_mep() -> pd.DataFrame:
    """Trae el dólar MEP desde dolarapi.com (calculado como ratio AL30/AL30D)."""
    try:
        r = requests.get(MEP_API_URL, timeout=10)
        r.raise_for_status()
        d = r.json()
        # dolarapi devuelve compra/venta; usamos venta como referencia de precio
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


def color_variacion(val):
    if val is None or pd.isna(val):
        return ""
    color = "#1a7f37" if val >= 0 else "#c0392b"
    return f"color: {color}; font-weight: 600;"


# ----------------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------------

st.title("📊 Screener Personalizado")
st.caption(f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

with st.sidebar:
    st.header("Universo de activos")
    stocks_input = st.text_area("Acciones NYSE (tickers separados por coma)", DEFAULT_STOCKS)
    etfs_input = st.text_area("ETFs (tickers separados por coma)", DEFAULT_ETFS)
    show_commodities = st.checkbox("Mostrar commodities (Oro / Plata)", value=True)
    show_mep = st.checkbox("Mostrar Dólar MEP", value=True)
    if st.button("🔄 Refrescar datos"):
        st.cache_data.clear()

stock_tickers = [t.strip().upper() for t in stocks_input.split(",") if t.strip()]
etf_tickers = [t.strip().upper() for t in etfs_input.split(",") if t.strip()]

frames = []

if stock_tickers:
    st.subheader("Acciones")
    df_stocks = get_yf_data(stock_tickers)
    frames.append(df_stocks)
    st.dataframe(
        df_stocks.style.map(color_variacion, subset=["Variación %"]),
        use_container_width=True, hide_index=True,
    )

if etf_tickers:
    st.subheader("ETFs")
    df_etfs = get_yf_data(etf_tickers)
    frames.append(df_etfs)
    st.dataframe(
        df_etfs.style.map(color_variacion, subset=["Variación %"]),
        use_container_width=True, hide_index=True,
    )

if show_commodities:
    st.subheader("Commodities")
    df_comm = get_yf_data(list(COMMODITY_TICKERS.keys()))
    df_comm["Nombre"] = df_comm["Ticker"].map(COMMODITY_TICKERS)
    frames.append(df_comm)
    st.dataframe(
        df_comm.style.map(color_variacion, subset=["Variación %"]),
        use_container_width=True, hide_index=True,
    )

if show_mep:
    st.subheader("Tipo de Cambio")
    df_mep = get_mep()
    frames.append(df_mep)
    st.dataframe(df_mep, use_container_width=True, hide_index=True)

st.divider()
st.caption(
    "Fuentes: Yahoo Finance (acciones, ETFs, commodities) vía yfinance · "
    "dolarapi.com (Dólar MEP, calculado como AL30/AL30D). "
    "Los datos de Yahoo Finance pueden tener demora de hasta 15-20 minutos."
)
