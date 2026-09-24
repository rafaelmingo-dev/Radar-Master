from __future__ import annotations

import re
import unicodedata
import pandas as pd

# Funções abaixo copiadas do app.py do Valuation para o Radar Mestre.
# Elas não recalculam o motor: traduzem o snapshot exatamente como o painel original.

def _normalize_text(value) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text).strip().lower()

def _as_dataframe(value):
    if isinstance(value, pd.DataFrame):
        return value.copy()
    if isinstance(value, list):
        try:
            return pd.DataFrame(value)
        except Exception:
            return pd.DataFrame()
    if isinstance(value, dict):
        try:
            return pd.DataFrame(value)
        except Exception:
            try:
                return pd.DataFrame.from_dict(value, orient="index")
            except Exception:
                return pd.DataFrame()
    return pd.DataFrame()

def _ensure_asset_column(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    if "Ativo" in out.columns:
        out["Ativo"] = out["Ativo"].astype(str)
        return out

    normalized = {_normalize_text(c): c for c in out.columns}
    for candidate in ("ativo", "symbol", "ticker"):
        if candidate in normalized:
            out = out.rename(columns={normalized[candidate]: "Ativo"})
            out["Ativo"] = out["Ativo"].astype(str)
            return out

    idx_name = out.index.name
    if idx_name is not None and _normalize_text(idx_name) in {"ativo", "symbol", "ticker"}:
        out = out.reset_index().rename(columns={idx_name: "Ativo"})
        out["Ativo"] = out["Ativo"].astype(str)
        return out

    if not isinstance(out.index, pd.RangeIndex):
        out = out.reset_index().rename(columns={"index": "Ativo"})
        out["Ativo"] = out["Ativo"].astype(str)

    return out

def _find_detailed_decision_table(snapshot) -> pd.DataFrame:
    """
    Procura no snapshot a tabela final individual por ativo produzida pelo motor.
    A identificação é feita pelo conteúdo das colunas, sem depender do nome da
    variável usada no valuation_engine.py.
    """
    tables = snapshot.get("tables", {}) if isinstance(snapshot, dict) else {}
    if not isinstance(tables, dict):
        return pd.DataFrame()

    signatures = (
        "bom ativo para carteira",
        "empresa forte",
        "motivo da qualidade",
        "evidencias da qualidade",
        "esta barato hoje",
        "preco esta atrativo",
        "motivo do preco",
        "evidencias do valuation",
        "conclusao direta",
        "leitura para carteira",
        "o que fazer",
    )

    best = pd.DataFrame()
    best_score = -1

    for raw in tables.values():
        df = _ensure_asset_column(_as_dataframe(raw))
        if df.empty or "Ativo" not in df.columns:
            continue

        normalized_columns = {_normalize_text(c) for c in df.columns}
        score = sum(1 for sig in signatures if sig in normalized_columns)

        if score > best_score:
            best_score = score
            best = df

    # Exige que seja de fato uma tabela explicativa e não apenas uma tabela
    # genérica do Radar.
    if best_score >= 3:
        return best

    return pd.DataFrame()

def _decision_lookup(snapshot):
    df = _find_detailed_decision_table(snapshot)
    if df.empty:
        return {}

    lookup = {}
    for _, row in df.iterrows():
        symbol = str(row.get("Ativo", "")).strip()
        if symbol:
            lookup[symbol] = row.to_dict()
    return lookup

def _parse_number(value):
    """
    Conversão apenas para FORMATAÇÃO da interface.
    Não participa de nenhum cálculo econômico.
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        try:
            if pd.isna(value):
                return None
        except Exception:
            pass
        return float(value)

    text = str(value).strip()
    if not text:
        return None

    text = text.replace("R$", "").replace("%", "").replace("/100", "").strip()

    if "," in text:
        text = text.replace(".", "").replace(",", ".")

    try:
        return float(text)
    except Exception:
        return None

def _fmt_money(value):
    n = _parse_number(value)
    if n is None:
        text = "" if value is None else str(value).strip()
        return text or "n/d"

    return f"R$ {n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def _fmt_score(value):
    n = _parse_number(value)
    if n is None:
        text = "" if value is None else str(value).strip()
        return text or "n/d"
    return f"{n:.1f}/100".replace(".", ",")

def _fmt_percent(value):
    """
    Formata percentuais sem alterar o valor econômico.

    O radar_df mantém Upside/Downside como razão decimal em campos numéricos
    (ex.: -0.196 = -19,6%). Quando o valor já chega como texto com "%", ele
    já está em pontos percentuais e não deve ser multiplicado novamente.
    """
    n = _parse_number(value)
    if n is None:
        text = "" if value is None else str(value).strip()
        return text or "n/d"

    if isinstance(value, str):
        if "%" not in value:
            n *= 100.0
    else:
        n *= 100.0

    return f"{n:+.1f}%".replace(".", ",")

def _detail_value(detail: dict, *keys):
    for key in keys:
        if key in detail:
            value = str(detail[key]).strip()
            if value and value.lower() != "nan":
                return value
    return None

def _quality_answer(row: pd.Series, detail: dict | None):
    """
    Não cria corte novo de Quality Score.

    Se o motor já trouxe a conclusão individual, usa essa conclusão.
    Caso contrário, usa Classe de qualidade + Quality Score já existentes.
    """
    detail = detail or {}

    explicit = _detail_value(
        detail,
        "Bom ativo para carteira?",
        "Empresa forte?",
    )
    if explicit:
        return explicit

    quality_class = str(row.get("Classe de qualidade", "")).strip()
    qn = _normalize_text(quality_class)
    score = _fmt_score(row.get("Quality Score"))

    if "excelente" in qn:
        return f"SIM — EXCELENTE NO GRUPO ({score})"

    if "forte" in qn:
        # Importante: evita transformar automaticamente "forte no grupo"
        # em "excelente absoluto". O score permanece visível para julgamento.
        return f"ATENÇÃO — FORTE NO GRUPO ({score})"

    if "intermedi" in qn:
        return f"NÃO PRIORITÁRIA — QUALIDADE INTERMEDIÁRIA ({score})"

    if quality_class:
        return f"NÃO PRIORITÁRIA — {quality_class.upper()} ({score})"

    return f"QUALIDADE NÃO CLASSIFICADA ({score})"

def _quality_is_approved(row: pd.Series) -> bool:
    """Usa somente a classe de qualidade já calculada pelo motor."""
    quality_class = _normalize_text(row.get("Classe de qualidade", ""))
    return "excelente" in quality_class or "forte" in quality_class

def _valuation_numbers(row: pd.Series):
    """
    Retorna preço, alvo e diferença percentual a partir dos campos já calculados.
    A diferença é derivada apenas quando o campo Upside/Downside não estiver disponível.
    """
    price = _parse_number(row.get("Preço atual"))
    target = _parse_number(row.get("Alvo validado 12m"))

    raw_upside = row.get("Upside/Downside")
    upside = _parse_number(raw_upside)

    if upside is not None:
        if isinstance(raw_upside, str) and "%" in raw_upside:
            upside_ratio = upside / 100.0
        else:
            upside_ratio = upside
    elif price is not None and target is not None and price != 0:
        upside_ratio = target / price - 1.0
    else:
        upside_ratio = None

    return price, target, upside_ratio

def _conclusive_valuation(row: pd.Series) -> str:
    """
    Valuation FINAL conclusivo pelo alvo oficial validado de 12 meses.

    Não cria margem de segurança nem novo preço-alvo:
    - alvo final > preço atual  -> ATRATIVO pelo alvo final;
    - alvo final < preço atual  -> CARO pelo alvo final;
    - alvo final = preço atual  -> NO PREÇO JUSTO;
    - sem alvo validado         -> N/D (ex.: holding que exige NAV/SOTP).

    A divergência entre os quatro métodos passa a ser tratada como CONFIANÇA/AUDITORIA,
    e não como ausência de conclusão do valuation final.
    """
    price, target, _ = _valuation_numbers(row)

    if price is None or target is None or price <= 0:
        return "N/D — SEM ALVO VALIDADO / NAV-SOTP PENDENTE"

    if target > price:
        return "ATRATIVO — ALVO FINAL ACIMA DO PREÇO"
    if target < price:
        return "CARO — ALVO FINAL ABAIXO DO PREÇO"
    return "NO PREÇO JUSTO — ALVO FINAL = PREÇO"

def _valuation_direction(row: pd.Series) -> str:
    verdict = _normalize_text(_conclusive_valuation(row))
    if "atrativo" in verdict:
        return "atrativo"
    if "caro" in verdict:
        return "caro"
    if "preco justo" in verdict:
        return "justo"
    return "nd"

def _method_audit_text(row: pd.Series) -> str:
    status = str(row.get("Valuation Status", "n/d")).strip() or "n/d"
    confidence = str(row.get("Confiança", "n/d")).strip() or "n/d"
    return f"{status} | confiança {confidence}"

def _price_answer(row: pd.Series, detail: dict | None):
    """
    Responde de forma conclusiva usando o ALVO FINAL VALIDADO do próprio motor.

    O antigo Valuation Status (consenso/divergência dos quatro métodos) continua
    preservado como auditoria de confiança, mas não impede o veredito final.
    """
    return _conclusive_valuation(row)

def _portfolio_conclusion(row: pd.Series, detail: dict | None):
    """
    Combina a classe de qualidade já calculada com o valuation final conclusivo.
    Não cria score, alvo ou margem de segurança novos.
    """
    quality_ok = _quality_is_approved(row)
    direction = _valuation_direction(row)

    if direction == "nd":
        return "⚪ PREÇO NÃO CLASSIFICÁVEL — SEM ALVO VALIDADO / NAV-SOTP PENDENTE"

    if quality_ok and direction == "atrativo":
        return "⭐ BOA EMPRESA + VALUATION ATRATIVO"

    if quality_ok and direction == "caro":
        return "🟡 BOA EMPRESA, MAS VALUATION CARO"

    if quality_ok and direction == "justo":
        return "🟢 BOA EMPRESA — NO PREÇO JUSTO DO MODELO"

    if (not quality_ok) and direction == "atrativo":
        return "🔎 PREÇO ATRATIVO, MAS QUALIDADE NÃO PRIORITÁRIA"

    if (not quality_ok) and direction == "caro":
        return "🔴 NÃO PRIORITÁRIO — QUALIDADE NÃO PRIORITÁRIA + VALUATION CARO"

    return "⚪ MONITORAR — QUALIDADE NÃO PRIORITÁRIA"

def _quality_reason(row: pd.Series, detail: dict | None):
    detail = detail or {}

    explicit = _detail_value(
        detail,
        "Motivo da qualidade — números",
        "Evidências da qualidade",
    )
    if explicit:
        return explicit

    score = _fmt_score(row.get("Quality Score"))
    cls = str(row.get("Classe de qualidade", "n/d"))

    return (
        f"Quality Score {score}; classificação relativa: {cls}. "
        "O detalhamento técnico abaixo mostra ROE, lucros, caixa, dívida, crescimento e dividendos."
    )

def _valuation_reason(row: pd.Series, detail: dict | None):
    """
    Explica DUAS coisas separadas:
    1) o veredito final, sempre baseado no alvo oficial validado;
    2) por que os métodos podem divergir e qual é a confiança desse veredito.
    """
    detail = detail or {}

    price, target, upside_ratio = _valuation_numbers(row)
    verdict = _conclusive_valuation(row)
    method_status = str(row.get("Valuation Status", "n/d")).strip() or "n/d"
    confidence = str(row.get("Confiança", "n/d")).strip() or "n/d"

    price_txt = _fmt_money(price)
    target_txt = _fmt_money(target)
    upside_txt = _fmt_percent(upside_ratio) if upside_ratio is not None else "n/d"

    explicit = _detail_value(
        detail,
        "Motivo do preço — números",
        "Evidências do valuation",
    )

    base = (
        f"VEREDITO FINAL: {verdict}. Preço atual {price_txt}; alvo oficial validado 12m "
        f"{target_txt}; diferença {upside_txt}. Auditoria dos métodos: {method_status}. "
        f"Confiança: {confidence}."
    )

    if explicit:
        return base + " " + explicit

    return base

def _what_to_do(row: pd.Series, detail: dict | None):
    quality_ok = _quality_is_approved(row)
    direction = _valuation_direction(row)
    confidence = str(row.get("Confiança", "n/d")).strip() or "n/d"

    if direction == "nd":
        return "Não usar preço justo para decisão até existir alvo validado; para ITSA4, concluir NAV/SOTP."

    if quality_ok and direction == "atrativo":
        return (
            "Aprofundar a tese e os riscos específicos para eventual inclusão em carteira. "
            f"A confiança dos métodos é {confidence}; divergência reduz confiança, mas não muda o sinal do alvo final."
        )

    if quality_ok and direction == "caro":
        return (
            "Manter na watchlist e aguardar preço melhor ou aumento do alvo pelos fundamentos. "
            f"A confiança dos métodos é {confidence}."
        )

    if quality_ok and direction == "justo":
        return "Manter na watchlist e avaliar a tese; o preço está praticamente no alvo final do modelo."

    if (not quality_ok) and direction == "atrativo":
        return (
            "O preço está abaixo do alvo final, mas a qualidade não é prioritária no Radar. "
            "Investigar a qualidade antes de considerar entrada."
        )

    return "Não priorizar no estado atual; qualidade não prioritária e/ou valuation caro pelo alvo final."

def _short_numeric_reason(row: pd.Series):
    """Resumo curto do veredito final + auditoria dos métodos."""
    price, target, upside_ratio = _valuation_numbers(row)
    return (
        f"Preço {_fmt_money(price)} • alvo {_fmt_money(target)} "
        f"({_fmt_percent(upside_ratio) if upside_ratio is not None else 'n/d'}) • "
        f"{_conclusive_valuation(row)} • métodos: {_method_audit_text(row)}"
    )

def _target_24m_from_snapshot(snapshot, symbol: str):
    """
    Lê o alvo estratégico de 24 meses diretamente dos resultados completos
    exportados pelo valuation_engine.py.

    O app.py NÃO calcula o alvo de 24 meses. Ele apenas lê:
      - validated_target_24m
      - validated_upside_24m
      - validated_annualized_24m

    FCFF e módulos equity ficam separados no snapshot, mas a interface expõe
    uma leitura única por ticker.
    """
    if not isinstance(snapshot, dict) or not symbol:
        return {
            "target_24m": None,
            "potential_24m": None,
            "annualized_24m": None,
            "source": None,
            "note": None,
            "error": None,
        }

    result = None
    fcff = snapshot.get("results_fcff", {})
    equity = snapshot.get("results_equity", {})

    if isinstance(fcff, dict) and symbol in fcff:
        result = fcff.get(symbol)
    elif isinstance(equity, dict) and symbol in equity:
        result = equity.get(symbol)

    if not isinstance(result, dict):
        return {
            "target_24m": None,
            "potential_24m": None,
            "annualized_24m": None,
            "source": None,
            "note": None,
            "error": None,
        }

    return {
        "target_24m": _parse_number(result.get("validated_target_24m")),
        "potential_24m": _parse_number(result.get("validated_upside_24m")),
        "annualized_24m": _parse_number(result.get("validated_annualized_24m")),
        "source": result.get("target_24m_source"),
        "note": result.get("target_24m_note"),
        "error": result.get("target_24m_error"),
    }

def _fmt_percent_ratio(value):
    """
    Formata razões decimais vindas diretamente do motor:
    0.25 -> +25,0%.
    """
    n = _parse_number(value)
    if n is None:
        return "n/d"
    return f"{n * 100.0:+.1f}%".replace(".", ",")

def build_clear_decision_table(snapshot, radar_df: pd.DataFrame) -> pd.DataFrame:
    """
    Visão executiva sem recalcular o valuation.

    IMPORTANTE PARA O STREAMLIT:
    Preço atual, alvos e potenciais permanecem em formato NUMÉRICO bruto.
    O app formata somente a apresentação.

    O alvo de 12 meses continua sendo o horizonte PRINCIPAL.
    O alvo de 24 meses é exibido como horizonte ESTRATÉGICO adicional.
    """
    if radar_df is None or radar_df.empty:
        return pd.DataFrame()

    details = _decision_lookup(snapshot)
    rows = []

    for _, row in radar_df.iterrows():
        symbol = str(row.get("Ativo", "")).strip()
        detail = details.get(symbol, {})
        horizon24 = _target_24m_from_snapshot(snapshot, symbol)

        rows.append(
            {
                "Ativo": symbol,
                "Qualidade para carteira": _quality_answer(row, detail),
                "Preço atual": row.get("Preço atual"),
                "Alvo validado 12m": row.get("Alvo validado 12m"),
                "Upside/Downside": row.get("Upside/Downside"),
                "Alvo validado 24m": horizon24["target_24m"],
                "Potencial preço 24m": horizon24["potential_24m"],
                "CAGR preço 24m": horizon24["annualized_24m"],
                "Valuation final": _conclusive_valuation(row),
                "Confiança": row.get("Confiança", "n/d"),
                "Auditoria dos métodos": row.get("Valuation Status", "n/d"),
                "Conclusão para carteira": _portfolio_conclusion(row, detail),
                "Motivo objetivo": _short_numeric_reason(row),
            }
        )

    return pd.DataFrame(rows)
