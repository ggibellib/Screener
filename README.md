# Screener Personalizado

App en Streamlit para ver ticker, nombre, precio y variación % de:
- Acciones NYSE
- ETFs
- Commodities (oro y plata, vía futuros GC=F / SI=F)
- Dólar MEP (vía dolarapi.com, calculado como AL30/AL30D)

## Cómo correrlo localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

Se abre en `http://localhost:8501`.

## Cómo compartirlo como web pública (gratis)

**Opción recomendada: Streamlit Community Cloud**

1. Subí esta carpeta (`app.py`, `requirements.txt`) a un repo de GitHub (puede ser privado).
2. Entrá a https://share.streamlit.io con tu cuenta de GitHub.
3. "New app" → elegís el repo → branch → `app.py` como archivo principal → Deploy.
4. En unos minutos te da una URL pública tipo `https://tu-app.streamlit.app` que podés compartir con quien quieras.

Es gratis para apps públicas, no requiere servidor propio, y cada vez que hagas
push a GitHub se redeploya solo.

**Alternativas** si preferís no depender de Streamlit Cloud: Render.com,
Railway.app o un VPS propio corriendo `streamlit run app.py --server.port 80`.

## Notas sobre las fuentes de datos

- **Yahoo Finance (yfinance)**: no es una API oficial, es una librería que
  consume el backend público de Yahoo Finance. Es gratis y bastante estable
  para este uso, pero Yahoo puede cambiar su backend sin aviso — si en algún
  momento deja de funcionar, avisame y lo migramos a una API paga
  (Financial Modeling Prep, Twelve Data, Finnhub tienen tiers gratuitos
  razonables).
- **MEP**: en vez de scrapear TradingView o BYMA (fragil, contra ToS), uso
  dolarapi.com, que ya calcula el MEP de la misma forma (bono en pesos /
  bono en dólares, típicamente AL30/AL30D) y es gratis y estable.
  Si en algún momento querés calcularlo vos mismo a partir de los precios
  crudos de AL30 y AL30D (por ejemplo si tenés cuenta en un bróker con API,
  como IOL o Rava), decime y adapto el código para pegarle a esa fuente.

## Personalización

- Cambiá `DEFAULT_STOCKS` y `DEFAULT_ETFS` en `app.py` para tu watchlist fija,
  o simplemente editá los tickers desde la barra lateral de la app.
- El cache de datos dura 60 segundos (`ttl=60`); ajustalo si querés datos más
  o menos frescos (cuidado con rate limits de Yahoo si lo bajás mucho).
