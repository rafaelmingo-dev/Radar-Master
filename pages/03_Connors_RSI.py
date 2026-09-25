# ============================================================================
# RADAR CONNORS RSI — STREAMLIT
# Baseado no Radar Connors RSI V3.1
# ============================================================================
#
# Metodologia preservada:
#   CRSI = [ RSI_Preço(3) + RSI_Streak(2) + PercentRank(100) ] / 3
#
# Níveis monitorados:
#   CRSI < 20
#   CRSI > 80
#
# Eventos monitorados:
#   CROSS ↑ 20
#   CROSS ↓ 80
#   SLOPE ↑ abaixo de 20
#   SLOPE ↓ acima de 80
#
# Visão operacional:
#   - somente CRSI confirmado nas tabelas principais
#   - snapshots do mesmo CRSI diário confirmado há 30D / 90D / 180D
#   - Percentil CRSI 1A preservado em janela de 1 ano
#   - CRSI atual/intraday continua calculado internamente para auditoria
#   - Status candle continua calculado internamente, mas não aparece nas tabelas
#
# Fonte de preços:
#   Yahoo Finance via yfinance (.SA)
#
# Deploy:
#   Streamlit Community Cloud + GitHub
# ============================================================================

from __future__ import annotations

import io
import time
import zipfile
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf


# ============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ============================================================================

st.set_page_config(
    page_title="Radar Connors RSI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.25rem;
            padding-bottom: 2.0rem;
            max-width: 1550px;
        }
        [data-testid="stMetric"] {
            background: #121820;
            border: 1px solid #26303c;
            border-radius: 8px;
            padding: 10px 12px;
        }
        [data-baseweb="tab-list"] {
            gap: 1.1rem;
            border-bottom: 1px solid #2b3440;
        }
        [data-baseweb="tab"] {
            padding-left: 0.1rem;
            padding-right: 0.1rem;
        }
        [data-baseweb="tab"][aria-selected="true"] {
            color: #ff4b55;
        }
        div[data-testid="stExpander"] {
            border: 1px solid #333d49;
            border-radius: 8px;
        }
        .small-note {
            color: #aeb6c2;
            font-size: 0.93rem;
            line-height: 1.45;
        }
        .headline-gap {
            margin-top: .1rem;
            margin-bottom: .3rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================================
# 2. PARÂMETROS
# ============================================================================

ATIVOS = [
    "VIVT3",
    "TUPY3",
    "ITUB4",
    "EGIE3",
    "TAEE11",
    "VALE3",
    "CMIG4",
    "EQTL3",
    "IRBR3",
    "BRSR6",
    "BBSE3",
    "BBDC4",
    "BPAC11",
    "ITSA4",
    "LEVE3",
    "B3SA3",
    "GGBR4",
    "GOAU4",
    "PSSA3",
    "RANI3",
    "BBAS3",
    "CPLE3",
    "CXSE3",
    "ABEV3",
    "PRIO3",
    "CPFE3",
    "GOLD11",
    "PETR4",
    "WEGE3",
    "CSMG3",
    "SBSP3",
    "RADL3",
    "BRAP4",
    "UNIP6",
    "KEPL3",
    "PNVL3",
    "SANB11",
    "INBR32",
    "CSAN3",
    "MRVE3",
]

RSI_PRECO = 3
RSI_STREAK = 2
PERCENT_RANK = 100

LOWER = 20.0
UPPER = 80.0

AUTO_ADJUST = True
TZ_B3 = ZoneInfo("America/Sao_Paulo")
HORARIO_CONFIRMACAO_DIARIA = dt_time(18, 15)
MIN_BARRAS_CRSI = PERCENT_RANK + 2

GERAR_AUDITORIA_TIMEFRAMES = True
TIMEFRAMES_LITERAIS = ["Diário", "Mensal", "Semestral", "Anual"]

CACHE_TTL_SEGUNDOS = 15 * 60


# ============================================================================
# 3. UTILITÁRIOS BÁSICOS
# ============================================================================


def ticker_yahoo(ticker: str) -> str:
    ticker = str(ticker).strip().upper()
    return ticker if ticker.endswith(".SA") else f"{ticker}.SA"



def normalizar_indice(series: pd.Series) -> pd.Series:
    s = pd.Series(series, copy=True)
    s.index = pd.to_datetime(s.index)

    try:
        s.index = s.index.tz_localize(None)
    except Exception:
        pass

    s = s.sort_index()
    s = s[~s.index.duplicated(keep="last")]
    s = pd.to_numeric(s, errors="coerce").dropna()
    s = s[s > 0]
    return s.astype(float)



def fmt_num(valor, casas: int = 2) -> str:
    if pd.isna(valor):
        return "N/D"
    return f"{float(valor):.{casas}f}".replace(".", ",")



def fmt_percent(valor, casas: int = 1) -> str:
    if pd.isna(valor):
        return "N/D"
    return f"{float(valor):.{casas}f}%".replace(".", ",")



def fmt_data(valor) -> str:
    if pd.isna(valor):
        return "N/D"
    return pd.Timestamp(valor).strftime("%d/%m/%Y")


# ============================================================================
# 4. RSI DE WILDER
# ============================================================================


def rsi_wilder(series: pd.Series, periodo: int) -> pd.Series:
    s = pd.Series(series, copy=True).astype(float)
    delta = s.diff()

    ganhos = delta.clip(lower=0.0)
    perdas = -delta.clip(upper=0.0)

    media_ganhos = ganhos.ewm(
        alpha=1.0 / periodo,
        adjust=False,
        min_periods=periodo,
    ).mean()

    media_perdas = perdas.ewm(
        alpha=1.0 / periodo,
        adjust=False,
        min_periods=periodo,
    ).mean()

    rs = media_ganhos / media_perdas
    rsi = 100.0 - (100.0 / (1.0 + rs))

    ambos_zero = (media_ganhos == 0) & (media_perdas == 0)
    somente_ganhos = (media_ganhos > 0) & (media_perdas == 0)
    somente_perdas = (media_ganhos == 0) & (media_perdas > 0)

    rsi = rsi.mask(ambos_zero, 50.0)
    rsi = rsi.mask(somente_ganhos, 100.0)
    rsi = rsi.mask(somente_perdas, 0.0)

    return rsi


# ============================================================================
# 5. STREAK
# ============================================================================


def calcular_streak(close: pd.Series) -> pd.Series:
    close = pd.Series(close, copy=True).astype(float)
    valores = close.to_numpy(dtype=float)
    streak = np.zeros(len(valores), dtype=float)

    for i in range(1, len(valores)):
        atual = valores[i]
        anterior = valores[i - 1]

        if np.isnan(atual) or np.isnan(anterior):
            streak[i] = 0.0
        elif atual > anterior:
            streak[i] = streak[i - 1] + 1.0 if streak[i - 1] > 0 else 1.0
        elif atual < anterior:
            streak[i] = streak[i - 1] - 1.0 if streak[i - 1] < 0 else -1.0
        else:
            streak[i] = 0.0

    return pd.Series(streak, index=close.index, name="Streak")


# ============================================================================
# 6. PERCENT RANK
# ============================================================================


def calcular_percent_rank(close: pd.Series, periodo: int = 100) -> pd.Series:
    """
    PercentRank do retorno atual contra os `periodo` retornos anteriores.
    O retorno atual não participa da própria janela histórica.
    """
    close = pd.Series(close, copy=True).astype(float)
    retornos = close.pct_change(fill_method=None)
    valores = retornos.to_numpy(dtype=float)
    resultado = np.full(len(valores), np.nan, dtype=float)

    for i in range(periodo + 1, len(valores)):
        atual = valores[i]
        historico = valores[i - periodo:i]

        if np.isnan(atual) or np.isnan(historico).any():
            continue

        menores = np.sum(historico < atual)
        resultado[i] = (menores / periodo) * 100.0

    return pd.Series(resultado, index=close.index, name="PercentRank")


# ============================================================================
# 7. CONNORS RSI 3 / 2 / 100
# ============================================================================


def calcular_connors_rsi(close: pd.Series) -> pd.DataFrame:
    close = normalizar_indice(close)

    rsi_preco = rsi_wilder(close, RSI_PRECO)
    streak = calcular_streak(close)
    rsi_streak = rsi_wilder(streak, RSI_STREAK)
    percent_rank = calcular_percent_rank(close, PERCENT_RANK)

    df = pd.DataFrame(index=close.index)
    df["Close"] = close
    df["RSI_Preco"] = rsi_preco
    df["Streak"] = streak
    df["RSI_Streak"] = rsi_streak
    df["PercentRank"] = percent_rank
    df["CRSI"] = (
        df["RSI_Preco"] + df["RSI_Streak"] + df["PercentRank"]
    ) / 3.0

    return df


# ============================================================================
# 8. CLASSIFICAÇÕES, EVENTOS E DISTÂNCIAS
# ============================================================================


def classificar_zona(crsi) -> str:
    if pd.isna(crsi):
        return "N/D"
    if crsi < LOWER:
        return "Abaixo de 20"
    if crsi > UPPER:
        return "Acima de 80"
    return "Entre 20 e 80"



def classificar_slope(atual, anterior) -> str:
    if pd.isna(atual) or pd.isna(anterior):
        return "N/D"
    if atual > anterior:
        return "↑"
    if atual < anterior:
        return "↓"
    return "→"



def identificar_evento(atual, anterior) -> str:
    if pd.isna(atual) or pd.isna(anterior):
        return "N/D"

    if anterior < LOWER and atual >= LOWER:
        return "CROSS ↑ 20"
    if anterior > UPPER and atual <= UPPER:
        return "CROSS ↓ 80"
    if atual < LOWER and atual > anterior:
        return "SLOPE ↑ abaixo de 20"
    if atual > UPPER and atual < anterior:
        return "SLOPE ↓ acima de 80"
    if atual < LOWER:
        return "Abaixo de 20"
    if atual > UPPER:
        return "Acima de 80"
    if atual > anterior:
        return "SLOPE ↑"
    if atual < anterior:
        return "SLOPE ↓"
    return "Neutro"



def distancia_limite_20_80(crsi):
    if pd.isna(crsi):
        return np.nan, "N/D"

    if crsi < LOWER:
        d = LOWER - crsi
        return d, f"{d:.2f} abaixo de 20"

    if crsi > UPPER:
        d = crsi - UPPER
        return d, f"{d:.2f} acima de 80"

    d20 = crsi - LOWER
    d80 = UPPER - crsi

    if d20 <= d80:
        return d20, f"{d20:.2f} acima de 20"

    return d80, f"{d80:.2f} abaixo de 80"



def contar_pregoes_extremo(crsi_series: pd.Series):
    s = pd.Series(crsi_series).dropna()

    if s.empty:
        return 0, "Nenhum"

    ultimo = float(s.iloc[-1])

    if ultimo > UPPER:
        condicao = s > UPPER
        zona = "> 80"
    elif ultimo < LOWER:
        condicao = s < LOWER
        zona = "< 20"
    else:
        return 0, "Nenhum"

    contador = 0
    for valor in condicao.iloc[::-1]:
        if bool(valor):
            contador += 1
        else:
            break

    return contador, zona


# ============================================================================
# 9. DOWNLOAD DE MERCADO — LOTE + FALLBACK INDIVIDUAL
# ============================================================================


def extrair_close_lote(dados: pd.DataFrame, simbolo: str) -> pd.Series:
    if dados is None or dados.empty:
        return pd.Series(dtype=float)

    try:
        if isinstance(dados.columns, pd.MultiIndex):
            nivel0 = dados.columns.get_level_values(0)
            if "Close" not in nivel0:
                return pd.Series(dtype=float)

            close = dados["Close"]
            if isinstance(close, pd.DataFrame):
                if simbolo in close.columns:
                    return normalizar_indice(close[simbolo])
                return pd.Series(dtype=float)

        if "Close" in dados.columns:
            return normalizar_indice(dados["Close"])

    except Exception:
        return pd.Series(dtype=float)

    return pd.Series(dtype=float)



def baixar_close_individual(ticker: str, tentativas: int = 3) -> pd.Series:
    simbolo = ticker_yahoo(ticker)
    erros = []

    for tentativa in range(1, tentativas + 1):
        try:
            dados = yf.download(
                simbolo,
                period="max",
                interval="1d",
                auto_adjust=AUTO_ADJUST,
                actions=False,
                progress=False,
                threads=False,
                timeout=25,
            )
            close = extrair_close_lote(dados, simbolo)
            if not close.empty:
                return close
        except Exception as erro:
            erros.append(str(erro))
        time.sleep(tentativa * 1.0)

    try:
        dados = yf.Ticker(simbolo).history(
            period="max",
            interval="1d",
            auto_adjust=AUTO_ADJUST,
            actions=False,
            repair=True,
        )
        if dados is not None and not dados.empty and "Close" in dados.columns:
            close = normalizar_indice(dados["Close"])
            if not close.empty:
                return close
    except Exception as erro:
        erros.append(str(erro))

    raise RuntimeError(" | ".join(erros) if erros else "Sem dados de mercado.")



def baixar_dados_lote(ativos: list[str]):
    simbolos = [ticker_yahoo(t) for t in ativos]
    closes: dict[str, pd.Series] = {}
    falhas: dict[str, str] = {}

    try:
        dados = yf.download(
            simbolos,
            period="max",
            interval="1d",
            auto_adjust=AUTO_ADJUST,
            actions=False,
            progress=False,
            threads=True,
            group_by="column",
            timeout=35,
        )
    except Exception:
        dados = pd.DataFrame()

    for ticker, simbolo in zip(ativos, simbolos):
        close = extrair_close_lote(dados, simbolo)

        if close.empty:
            try:
                close = baixar_close_individual(ticker)
            except Exception as erro:
                falhas[ticker] = str(erro)
                continue

        closes[ticker] = close

    return closes, falhas


# ============================================================================
# 10. CANDLE ATUAL VS CONFIRMADO
# ============================================================================


def status_ultimo_candle(close: pd.Series) -> str:
    if close.empty:
        return "N/D"

    agora = datetime.now(TZ_B3)
    hoje = agora.date()
    ultima_data = pd.Timestamp(close.index[-1]).date()

    if ultima_data < hoje:
        return "FECHADO"
    if ultima_data > hoje:
        return "VERIFICAR"
    if agora.time() < HORARIO_CONFIRMACAO_DIARIA:
        return "EM FORMAÇÃO"
    return "FECHADO"



def obter_close_confirmado(close: pd.Series):
    close = normalizar_indice(close)
    status = status_ultimo_candle(close)

    if status == "EM FORMAÇÃO" and len(close) >= 2:
        return close.iloc[:-1].copy(), status

    return close.copy(), status


# ============================================================================
# 11. SNAPSHOTS E ESTATÍSTICAS
# ============================================================================


def ultimos_crsi_validos(df_crsi: pd.DataFrame):
    validos = df_crsi["CRSI"].dropna()

    if validos.empty:
        return np.nan, np.nan, pd.NaT

    atual = float(validos.iloc[-1])
    data_atual = validos.index[-1]
    anterior = float(validos.iloc[-2]) if len(validos) >= 2 else np.nan

    return atual, anterior, data_atual



def obter_snapshot_crsi(crsi_series: pd.Series, data_alvo):
    s = pd.Series(crsi_series).dropna()

    if s.empty:
        return np.nan, pd.NaT

    data_alvo = pd.Timestamp(data_alvo)
    candidatos = s[s.index <= data_alvo]

    if candidatos.empty:
        return np.nan, pd.NaT

    return float(candidatos.iloc[-1]), candidatos.index[-1]



def estatisticas_crsi_1ano(crsi_series: pd.Series, data_referencia):
    s = pd.Series(crsi_series).dropna()

    if s.empty:
        return np.nan, np.nan, np.nan

    referencia = pd.Timestamp(data_referencia)
    inicio = referencia - pd.DateOffset(years=1)
    janela = s[(s.index >= inicio) & (s.index <= referencia)]

    if janela.empty:
        return np.nan, np.nan, np.nan

    atual = float(janela.iloc[-1])
    minimo = float(janela.min())
    maximo = float(janela.max())
    percentil = float(np.mean(janela.values <= atual) * 100.0)

    return minimo, maximo, percentil


# ============================================================================
# 12. AUDITORIA MATEMÁTICA
# ============================================================================


def auditar_ultima_linha_crsi(df_crsi: pd.DataFrame, tolerancia: float = 1e-10):
    validos = df_crsi.dropna(
        subset=["RSI_Preco", "RSI_Streak", "PercentRank", "CRSI"]
    )

    if validos.empty:
        return "N/D", np.nan

    linha = validos.iloc[-1]
    recalculado = (
        float(linha["RSI_Preco"])
        + float(linha["RSI_Streak"])
        + float(linha["PercentRank"])
    ) / 3.0

    erro = abs(recalculado - float(linha["CRSI"]))

    componentes_ok = all(
        0.0 <= float(linha[col]) <= 100.0
        for col in ["RSI_Preco", "RSI_Streak", "PercentRank", "CRSI"]
    )

    formula_ok = erro <= tolerancia
    return ("OK" if formula_ok and componentes_ok else "ERRO"), erro


# ============================================================================
# 13. TIMEFRAMES LITERAIS — AUDITORIA
# ============================================================================


def agregar_timeframe_literal(close: pd.Series, timeframe: str) -> pd.Series:
    close = normalizar_indice(close)

    if timeframe == "Diário":
        return close

    df = close.to_frame("Close")

    if timeframe == "Mensal":
        return (
            df.groupby([df.index.year, df.index.month], sort=True)
            .tail(1)["Close"]
        )

    if timeframe == "Semestral":
        semestre = np.where(df.index.month <= 6, 1, 2)
        return (
            df.groupby([df.index.year, semestre], sort=True)
            .tail(1)["Close"]
        )

    if timeframe == "Anual":
        return df.groupby(df.index.year, sort=True).tail(1)["Close"]

    raise ValueError(f"Timeframe inválido: {timeframe}")


# ============================================================================
# 14. ANÁLISE DE UM ATIVO
# ============================================================================


def analisar_ativo(ticker: str, close: pd.Series):
    close = normalizar_indice(close)
    close_confirmado, status_candle = obter_close_confirmado(close)

    if len(close_confirmado) < MIN_BARRAS_CRSI:
        raise ValueError(
            f"Histórico insuficiente: {len(close_confirmado)} barras; "
            f"mínimo necessário {MIN_BARRAS_CRSI}."
        )

    # Atual/intraday — preservado para auditoria.
    crsi_atual_df = calcular_connors_rsi(close)
    crsi_atual, crsi_atual_anterior, data_atual = ultimos_crsi_validos(
        crsi_atual_df
    )

    # Confirmado — base das tabelas operacionais.
    crsi_conf_df = calcular_connors_rsi(close_confirmado)
    crsi_conf, crsi_conf_anterior, data_conf = ultimos_crsi_validos(
        crsi_conf_df
    )

    # Componentes atuais/intraday preservados como no radar anterior.
    validos_atual = crsi_atual_df.dropna(subset=["CRSI"])
    if validos_atual.empty:
        comp = {
            "RSI preço": np.nan,
            "Streak": np.nan,
            "RSI streak": np.nan,
            "PercentRank": np.nan,
        }
    else:
        linha = validos_atual.iloc[-1]
        comp = {
            "RSI preço": float(linha["RSI_Preco"]),
            "Streak": float(linha["Streak"]),
            "RSI streak": float(linha["RSI_Streak"]),
            "PercentRank": float(linha["PercentRank"]),
        }

    preco_atual = float(close.iloc[-1]) if len(close) else np.nan
    preco_confirmado = (
        float(close_confirmado.iloc[-1]) if len(close_confirmado) else np.nan
    )

    # Snapshots do MESMO CRSI diário confirmado: 30 / 90 / 180 dias corridos.
    if pd.notna(data_conf):
        referencia = pd.Timestamp(data_conf)

        crsi_30d, data_30d = obter_snapshot_crsi(
            crsi_conf_df["CRSI"], referencia - pd.Timedelta(days=30)
        )
        crsi_90d, data_90d = obter_snapshot_crsi(
            crsi_conf_df["CRSI"], referencia - pd.Timedelta(days=90)
        )
        crsi_180d, data_180d = obter_snapshot_crsi(
            crsi_conf_df["CRSI"], referencia - pd.Timedelta(days=180)
        )

        minimo_1a, maximo_1a, percentil_1a = estatisticas_crsi_1ano(
            crsi_conf_df["CRSI"], referencia
        )
    else:
        crsi_30d = crsi_90d = crsi_180d = np.nan
        data_30d = data_90d = data_180d = pd.NaT
        minimo_1a = maximo_1a = percentil_1a = np.nan

    delta_1d = (
        crsi_conf - crsi_conf_anterior
        if pd.notna(crsi_conf) and pd.notna(crsi_conf_anterior)
        else np.nan
    )
    delta_30d = (
        crsi_conf - crsi_30d
        if pd.notna(crsi_conf) and pd.notna(crsi_30d)
        else np.nan
    )
    delta_90d = (
        crsi_conf - crsi_90d
        if pd.notna(crsi_conf) and pd.notna(crsi_90d)
        else np.nan
    )
    delta_180d = (
        crsi_conf - crsi_180d
        if pd.notna(crsi_conf) and pd.notna(crsi_180d)
        else np.nan
    )

    evento_atual = identificar_evento(crsi_atual, crsi_atual_anterior)
    evento_confirmado = identificar_evento(crsi_conf, crsi_conf_anterior)

    dist_atual_num, dist_atual_txt = distancia_limite_20_80(crsi_atual)
    dist_conf_num, dist_conf_txt = distancia_limite_20_80(crsi_conf)

    preg_ext_atual, zona_ext_atual = contar_pregoes_extremo(
        crsi_atual_df["CRSI"]
    )
    preg_ext_conf, zona_ext_conf = contar_pregoes_extremo(
        crsi_conf_df["CRSI"]
    )

    auditoria_crsi, erro_formula = auditar_ultima_linha_crsi(crsi_atual_df)

    principal = {
        "Ativo": ticker,
        "Preço atual": preco_atual,
        "Status candle": status_candle,
        "Data atual": data_atual,
        "CRSI atual": crsi_atual,
        "CRSI anterior atual": crsi_atual_anterior,
        "Slope atual": classificar_slope(crsi_atual, crsi_atual_anterior),
        "Zona atual": classificar_zona(crsi_atual),
        "Evento atual": evento_atual,
        "Evento atual é": (
            "PROVISÓRIO" if status_candle == "EM FORMAÇÃO" else "CONFIRMADO"
        ),
        "Distância atual": dist_atual_num,
        "Distância atual 20/80": dist_atual_txt,
        "Pregões extremo atual": preg_ext_atual,
        "Zona extremo atual": zona_ext_atual,
        "Data confirmada": data_conf,
        "Preço confirmado": preco_confirmado,
        "CRSI confirmado": crsi_conf,
        "CRSI confirmado anterior": crsi_conf_anterior,
        "Slope confirmado": classificar_slope(crsi_conf, crsi_conf_anterior),
        "Zona confirmada": classificar_zona(crsi_conf),
        "Evento confirmado": evento_confirmado,
        "Distância confirmada": dist_conf_num,
        "Distância confirmada 20/80": dist_conf_txt,
        "Pregões extremo confirmado": preg_ext_conf,
        "Zona extremo confirmado": zona_ext_conf,
        "CRSI 30D": crsi_30d,
        "Data 30D": data_30d,
        "CRSI 90D": crsi_90d,
        "Data 90D": data_90d,
        "CRSI 180D": crsi_180d,
        "Data 180D": data_180d,
        "Δ CRSI 1D": delta_1d,
        "Δ CRSI 30D": delta_30d,
        "Δ CRSI 90D": delta_90d,
        "Δ CRSI 180D": delta_180d,
        "Mínimo CRSI 1A": minimo_1a,
        "Máximo CRSI 1A": maximo_1a,
        "Percentil CRSI 1A": percentil_1a,
        "RSI preço": comp["RSI preço"],
        "Streak": comp["Streak"],
        "RSI streak": comp["RSI streak"],
        "PercentRank": comp["PercentRank"],
        "Auditoria CRSI": auditoria_crsi,
        "Erro fórmula CRSI": erro_formula,
        "Pregões disponíveis": len(close),
        "Histórico desde": close.index.min(),
    }

    auditoria = []
    if GERAR_AUDITORIA_TIMEFRAMES:
        for timeframe in TIMEFRAMES_LITERAIS:
            close_tf = agregar_timeframe_literal(close, timeframe)
            barras = len(close_tf)

            if barras >= MIN_BARRAS_CRSI:
                crsi_tf = calcular_connors_rsi(close_tf)
                atual_tf, anterior_tf, data_tf = ultimos_crsi_validos(crsi_tf)
                evento_tf = identificar_evento(atual_tf, anterior_tf)
            else:
                atual_tf = np.nan
                anterior_tf = np.nan
                data_tf = close_tf.index[-1] if barras else pd.NaT
                evento_tf = "Dados insuficientes"

            auditoria.append(
                {
                    "Ativo": ticker,
                    "Timeframe": timeframe,
                    "Barras": barras,
                    "Barras necessárias": MIN_BARRAS_CRSI,
                    "CRSI": atual_tf,
                    "CRSI anterior": anterior_tf,
                    "Slope": classificar_slope(atual_tf, anterior_tf),
                    "Zona": classificar_zona(atual_tf),
                    "Evento": evento_tf,
                    "Data": data_tf,
                }
            )

    return principal, auditoria, crsi_conf_df


# ============================================================================
# 15. EXECUÇÃO COMPLETA — COM CACHE DO STREAMLIT
# ============================================================================


@st.cache_data(ttl=CACHE_TTL_SEGUNDOS, show_spinner=False)
def carregar_painel():
    closes, falhas_download = baixar_dados_lote(ATIVOS)

    principais = []
    auditoria_total = []
    erros = []
    historicos = {}

    for ticker in ATIVOS:
        if ticker not in closes:
            erros.append(
                {
                    "Ativo": ticker,
                    "Erro": falhas_download.get(ticker, "Sem dados de mercado."),
                }
            )
            continue

        try:
            principal, auditoria, crsi_conf_df = analisar_ativo(
                ticker, closes[ticker]
            )
            principais.append(principal)
            auditoria_total.extend(auditoria)
            historicos[ticker] = crsi_conf_df
        except Exception as erro:
            erros.append({"Ativo": ticker, "Erro": str(erro)})

    resultado = pd.DataFrame(principais)
    auditoria_tf = pd.DataFrame(auditoria_total)
    erros_df = pd.DataFrame(erros)

    if not resultado.empty:
        ordem_map = {ativo: i for i, ativo in enumerate(ATIVOS)}
        resultado["_ordem"] = resultado["Ativo"].map(ordem_map)
        resultado = (
            resultado.sort_values("_ordem")
            .drop(columns="_ordem")
            .reset_index(drop=True)
        )

    calculado_em = datetime.now(TZ_B3)
    return resultado, auditoria_tf, erros_df, historicos, calculado_em


# ============================================================================
# 16. TABELAS OPERACIONAIS
# ============================================================================


def construir_tabelas(resultado: pd.DataFrame):
    if resultado.empty:
        vazio = pd.DataFrame()
        return vazio, vazio, vazio, vazio, vazio

    colunas_radar = [
        "Ativo",
        "Preço atual",
        "CRSI confirmado",
        "CRSI 30D",
        "CRSI 90D",
        "CRSI 180D",
        "Percentil CRSI 1A",
        "Distância confirmada 20/80",
        "Pregões extremo confirmado",
        "Zona extremo confirmado",
        "Slope confirmado",
        "Evento confirmado",
        "Auditoria CRSI",
    ]
    radar = resultado[colunas_radar].copy()

    matriz = resultado[
        [
            "Ativo",
            "CRSI 30D",
            "CRSI 90D",
            "CRSI 180D",
            "Percentil CRSI 1A",
        ]
    ].copy()

    eventos_relevantes = {
        "CROSS ↑ 20",
        "CROSS ↓ 80",
        "SLOPE ↑ abaixo de 20",
        "SLOPE ↓ acima de 80",
        "Abaixo de 20",
        "Acima de 80",
    }
    eventos = resultado[
        resultado["Evento confirmado"].isin(eventos_relevantes)
    ].copy()

    colunas_eventos = [
        "Ativo",
        "Preço atual",
        "CRSI confirmado",
        "Distância confirmada 20/80",
        "Pregões extremo confirmado",
        "Zona extremo confirmado",
        "Slope confirmado",
        "Evento confirmado",
        "Percentil CRSI 1A",
    ]
    eventos = eventos[colunas_eventos].copy() if not eventos.empty else pd.DataFrame(columns=colunas_eventos)

    componentes = resultado[
        [
            "Ativo",
            "CRSI atual",
            "RSI preço",
            "Streak",
            "RSI streak",
            "PercentRank",
            "Auditoria CRSI",
        ]
    ].copy()

    evolucao = resultado[
        [
            "Ativo",
            "CRSI confirmado",
            "Δ CRSI 1D",
            "Δ CRSI 30D",
            "Δ CRSI 90D",
            "Δ CRSI 180D",
            "Mínimo CRSI 1A",
            "Máximo CRSI 1A",
            "Percentil CRSI 1A",
            "Pregões extremo confirmado",
            "Zona extremo confirmado",
        ]
    ].copy()

    return radar, matriz, eventos, componentes, evolucao


# ============================================================================
# 17. ESTILOS DAS TABELAS
# ============================================================================


def css_crsi(valor):
    if pd.isna(valor):
        return "color: #7f8894;"
    if float(valor) < LOWER:
        return (
            "background-color: #184a35; color: #f6fff9; "
            "font-weight: 700;"
        )
    if float(valor) > UPPER:
        return (
            "background-color: #573036; color: #fff8f8; "
            "font-weight: 700;"
        )
    return ""



def css_auditoria(valor):
    if valor == "OK":
        return "color: #a9e7c7; font-weight: 700;"
    if valor == "ERRO":
        return "background-color: #573036; color: #fff8f8; font-weight: 700;"
    return ""



def estilizar_radar(df: pd.DataFrame):
    if df.empty:
        return df

    crsi_cols = [
        c
        for c in ["CRSI confirmado", "CRSI 30D", "CRSI 90D", "CRSI 180D"]
        if c in df.columns
    ]

    formatadores = {}
    for col in ["Preço atual", "CRSI confirmado", "CRSI 30D", "CRSI 90D", "CRSI 180D"]:
        if col in df.columns:
            formatadores[col] = lambda x: fmt_num(x, 2)
    if "Percentil CRSI 1A" in df.columns:
        formatadores["Percentil CRSI 1A"] = lambda x: fmt_percent(x, 1)

    styler = df.style.format(formatadores, na_rep="N/D")
    if crsi_cols:
        styler = styler.map(css_crsi, subset=crsi_cols)
    if "Auditoria CRSI" in df.columns:
        styler = styler.map(css_auditoria, subset=["Auditoria CRSI"])

    return styler



def estilizar_matriz(df: pd.DataFrame):
    if df.empty:
        return df

    formatadores = {
        "CRSI 30D": lambda x: fmt_num(x, 2),
        "CRSI 90D": lambda x: fmt_num(x, 2),
        "CRSI 180D": lambda x: fmt_num(x, 2),
        "Percentil CRSI 1A": lambda x: fmt_percent(x, 1),
    }

    return (
        df.style
        .format(formatadores, na_rep="N/D")
        .map(css_crsi, subset=["CRSI 30D", "CRSI 90D", "CRSI 180D"])
    )


# ============================================================================
# 18. EXPORTAÇÕES
# ============================================================================


def dataframe_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")



def gerar_zip_csvs(
    radar: pd.DataFrame,
    matriz: pd.DataFrame,
    eventos: pd.DataFrame,
    resultado: pd.DataFrame,
    auditoria_tf: pd.DataFrame,
    erros_df: pd.DataFrame,
) -> bytes:
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("radar_connors.csv", dataframe_csv_bytes(radar))
        zf.writestr("matriz_30d_90d_180d.csv", dataframe_csv_bytes(matriz))
        zf.writestr("eventos_20_80.csv", dataframe_csv_bytes(eventos))
        zf.writestr("detalhado.csv", dataframe_csv_bytes(resultado))

        if not auditoria_tf.empty:
            zf.writestr(
                "timeframes_literais.csv",
                dataframe_csv_bytes(auditoria_tf),
            )

        if not erros_df.empty:
            zf.writestr("erros.csv", dataframe_csv_bytes(erros_df))

    buffer.seek(0)
    return buffer.getvalue()



def gerar_excel_bytes(
    radar: pd.DataFrame,
    matriz: pd.DataFrame,
    eventos: pd.DataFrame,
    resultado: pd.DataFrame,
    componentes: pd.DataFrame,
    evolucao: pd.DataFrame,
    auditoria_tf: pd.DataFrame,
    erros_df: pd.DataFrame,
) -> bytes:
    buffer = io.BytesIO()

    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        radar.to_excel(writer, sheet_name="Radar", index=False)
        matriz.to_excel(writer, sheet_name="Matriz", index=False)
        eventos.to_excel(writer, sheet_name="Eventos_20_80", index=False)
        resultado.to_excel(writer, sheet_name="Detalhado", index=False)
        componentes.to_excel(writer, sheet_name="Componentes", index=False)
        evolucao.to_excel(writer, sheet_name="Evolucao", index=False)

        if not auditoria_tf.empty:
            auditoria_tf.to_excel(
                writer,
                sheet_name="Timeframes_Literais",
                index=False,
            )

        if not erros_df.empty:
            erros_df.to_excel(writer, sheet_name="Erros", index=False)

    buffer.seek(0)
    return buffer.getvalue()


# ============================================================================
# 19. CABEÇALHO E ATUALIZAÇÃO
# ============================================================================


titulo_col, botao_col = st.columns([7, 1])
with titulo_col:
    st.title("Radar Connors RSI")
with botao_col:
    st.write("")
    st.write("")
    if st.button("🔄 Atualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


with st.spinner("Atualizando dados e calculando o Connors RSI dos ativos..."):
    resultado, auditoria_tf, erros_df, historicos, calculado_em = carregar_painel()

if resultado.empty:
    st.error("Nenhum ativo foi processado com sucesso.")
    if not erros_df.empty:
        st.dataframe(erros_df, use_container_width=True, hide_index=True)
    st.stop()

radar, matriz, eventos, componentes, evolucao = construir_tabelas(resultado)

base_datas = pd.to_datetime(resultado["Data confirmada"], errors="coerce").dropna()
base_data = base_datas.max() if not base_datas.empty else pd.NaT

st.markdown(
    f"""
    <div class="small-note">
    Base CRSI: fechamento B3 <b>{fmt_data(base_data)}</b> •
    Painel calculado em <b>{calculado_em.strftime('%d/%m/%Y %H:%M')}</b> •
    CRSI 3/2/100 • 30D/90D/180D = snapshots do mesmo CRSI diário confirmado.
    </div>
    """,
    unsafe_allow_html=True,
)

if not erros_df.empty:
    ativos_erro = ", ".join(erros_df["Ativo"].astype(str).tolist())
    st.warning(
        f"{len(erros_df)} ativo(s) não puderam ser processados nesta atualização: "
        f"{ativos_erro}. Os demais foram calculados normalmente."
    )


# ============================================================================
# 20. ABAS PRINCIPAIS
# ============================================================================

aba_radar, aba_eventos, aba_detalhe, aba_como = st.tabs(
    ["Radar CRSI", "Eventos 20/80", "Detalhar ativo", "Como funciona"]
)


# ----------------------------------------------------------------------------
# ABA 1 — RADAR
# ----------------------------------------------------------------------------

with aba_radar:
    # A Matriz Rápida é a visão principal do painel.
    # Mantém somente 30D / 90D / 180D / Percentil 1A, conforme definido.
    st.header("Matriz rápida — 30D / 90D / 180D / Percentil 1A")

    st.dataframe(
        estilizar_matriz(matriz),
        use_container_width=True,
        hide_index=True,
        height=min(1120, 37 * (len(matriz) + 1)),
    )

    # A antiga visão rápida foi preservada, mas deixou de ocupar o destaque
    # principal. Ela continua disponível abaixo para consulta quando necessário.
    tabela_rapida = radar[
        [
            "Ativo",
            "Preço atual",
            "CRSI confirmado",
            "CRSI 30D",
            "CRSI 90D",
            "CRSI 180D",
            "Percentil CRSI 1A",
        ]
    ].copy()

    with st.expander("Ver visão rápida completa do Radar CRSI"):
        st.dataframe(
            estilizar_radar(tabela_rapida),
            use_container_width=True,
            hide_index=True,
            height=min(1120, 37 * (len(tabela_rapida) + 1)),
        )

    with st.expander("Ver tabela técnica completa do Radar CRSI"):
        st.dataframe(
            estilizar_radar(radar),
            use_container_width=True,
            hide_index=True,
            height=min(1120, 37 * (len(radar) + 1)),
        )

    col_zip, col_xlsx, _ = st.columns([1.6, 1.6, 4.8])

    with col_zip:
        st.download_button(
            "Baixar CSVs do painel",
            data=gerar_zip_csvs(
                radar,
                matriz,
                eventos,
                resultado,
                auditoria_tf,
                erros_df,
            ),
            file_name="radar_connors_rsi_csvs.zip",
            mime="application/zip",
            use_container_width=True,
        )

    with col_xlsx:
        st.download_button(
            "Baixar Excel completo",
            data=gerar_excel_bytes(
                radar,
                matriz,
                eventos,
                resultado,
                componentes,
                evolucao,
                auditoria_tf,
                erros_df,
            ),
            file_name="radar_connors_rsi.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            use_container_width=True,
        )


# ----------------------------------------------------------------------------
# ABA 2 — EVENTOS 20/80
# ----------------------------------------------------------------------------

with aba_eventos:
    st.header("Eventos confirmados relevantes — 20 / 80")

    st.caption(
        "Somente eventos baseados em CRSI confirmado. "
        "Movimentos intraday não entram nesta tabela."
    )

    if eventos.empty:
        st.success("Nenhum evento confirmado relevante no momento.")
    else:
        st.dataframe(
            estilizar_radar(eventos),
            use_container_width=True,
            hide_index=True,
            height=min(850, 42 * (len(eventos) + 1)),
        )


# ----------------------------------------------------------------------------
# ABA 3 — DETALHAR ATIVO
# ----------------------------------------------------------------------------

with aba_detalhe:
    st.header("Detalhar ativo")

    ativos_disponiveis = resultado["Ativo"].tolist()
    ativo_sel = st.selectbox("Ativo", ativos_disponiveis, index=0)

    linha = resultado.loc[resultado["Ativo"] == ativo_sel].iloc[0]

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Preço atual", fmt_num(linha["Preço atual"], 2))
    m2.metric("CRSI confirmado", fmt_num(linha["CRSI confirmado"], 2))
    m3.metric("CRSI 30D", fmt_num(linha["CRSI 30D"], 2))
    m4.metric("CRSI 90D", fmt_num(linha["CRSI 90D"], 2))
    m5.metric("CRSI 180D", fmt_num(linha["CRSI 180D"], 2))
    m6.metric("Percentil 1A", fmt_percent(linha["Percentil CRSI 1A"], 1))

    st.markdown(
        f"**Evento confirmado:** {linha['Evento confirmado']}  \n"
        f"**Zona confirmada:** {linha['Zona confirmada']}  \n"
        f"**Distância 20/80:** {linha['Distância confirmada 20/80']}  \n"
        f"**Pregões consecutivos no extremo:** {int(linha['Pregões extremo confirmado'])}  \n"
        f"**Data confirmada:** {fmt_data(linha['Data confirmada'])}"
    )

    hist = historicos.get(ativo_sel)
    if hist is not None and not hist.empty:
        hist_plot = hist[["CRSI"]].dropna().tail(260).copy()
        hist_plot["Limite 20"] = LOWER
        hist_plot["Limite 80"] = UPPER

        st.subheader("CRSI confirmado — histórico recente")
        st.line_chart(hist_plot, use_container_width=True)

    with st.expander("Ver dados técnicos do ativo"):
        campos = [
            "Ativo",
            "Preço atual",
            "Data confirmada",
            "CRSI confirmado",
            "CRSI confirmado anterior",
            "CRSI 30D",
            "Data 30D",
            "CRSI 90D",
            "Data 90D",
            "CRSI 180D",
            "Data 180D",
            "Δ CRSI 1D",
            "Δ CRSI 30D",
            "Δ CRSI 90D",
            "Δ CRSI 180D",
            "Mínimo CRSI 1A",
            "Máximo CRSI 1A",
            "Percentil CRSI 1A",
            "Slope confirmado",
            "Zona confirmada",
            "Evento confirmado",
            "Distância confirmada 20/80",
            "Pregões extremo confirmado",
            "Zona extremo confirmado",
            "Auditoria CRSI",
        ]
        detalhe = pd.DataFrame(
            {"Campo": campos, "Valor": [linha[c] for c in campos]}
        )
        st.dataframe(detalhe, use_container_width=True, hide_index=True)


# ----------------------------------------------------------------------------
# ABA 4 — COMO FUNCIONA
# ----------------------------------------------------------------------------

with aba_como:
    st.header("Como funciona")

    st.markdown(
        """
        **Connors RSI utilizado:** 3 / 2 / 100

        `CRSI = [RSI do preço(3) + RSI da streak(2) + PercentRank(100)] / 3`

        **CRSI confirmado** usa somente o último candle diário encerrado. Se o
        candle de hoje estiver em formação, ele é excluído da base operacional.

        **30D / 90D / 180D** são snapshots históricos do mesmo CRSI diário
        confirmado. O painel procura o último pregão disponível em ou antes da
        data-alvo de 30, 90 ou 180 dias corridos.

        **Percentil CRSI 1A** compara o CRSI confirmado mais recente com os
        valores de CRSI observados na janela de um ano. Ele não representa
        probabilidade de alta ou queda.

        **Regiões observadas:** CRSI abaixo de 20 e acima de 80. O painel também
        identifica CROSS de 20/80 e mudanças de slope nas regiões extremas.

        O CRSI atual/intraday e o status do candle continuam sendo calculados
        internamente para auditoria, mas não aparecem nas tabelas operacionais.
        """
    )

    st.subheader("Ativos monitorados")
    st.write(" • ".join(ATIVOS))

    with st.expander("Auditoria dos timeframes literais"):
        st.caption(
            "Mantida separadamente para Diário / Mensal / Semestral / Anual, "
            "sem alterar a leitura operacional diária do CRSI 3/2/100."
        )
        if auditoria_tf.empty:
            st.info("Auditoria indisponível nesta execução.")
        else:
            st.dataframe(
                auditoria_tf,
                use_container_width=True,
                hide_index=True,
                height=600,
            )


# ============================================================================
# 21. RODAPÉ
# ============================================================================

st.divider()
st.caption(
    "Dados obtidos via yfinance/Yahoo Finance. O painel é uma ferramenta de "
    "análise e não constitui recomendação de investimento."
)
