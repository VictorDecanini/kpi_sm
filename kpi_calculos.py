"""
kpi_calculos.py
Funções para calcular os KPIs a partir do DataFrame tratado.
Cada função é comentada e retorna valores prontos para exibir nos cards.
"""
import pandas as pd
import numpy as np

def kpi_sla_medio(df: pd.DataFrame, mask=None):
    if mask is None:
        mask = pd.Series(True, index=df.index)
    sub = df.loc[mask]
    # garantir que SLA exista — se não existir, recalculamos rápido
    if "SLA_DIAS_UTEIS" not in sub.columns:
        # tentativa de recalculo simples (dias corridos) como fallback
        sub["DATA_SOLICITACAO"] = pd.to_datetime(sub["DATA_SOLICITACAO"], errors="coerce")
        sub["DATA_CONCLUSAO"] = pd.to_datetime(sub["DATA_CONCLUSAO"], errors="coerce")
        sub["SLA_DIAS_UTEIS"] = (sub["DATA_CONCLUSAO"] - sub["DATA_SOLICITACAO"]).dt.days
    series = sub["SLA_DIAS_UTEIS"].dropna()
    if series.empty:
        return np.nan
    return round(series.mean(), 2)


def kpi_taxa_resolucao_1_dev(df: pd.DataFrame, mask=None):
    """
    Taxa de resolução na 1ª devolutiva:
    (# JIRAs únicos que possuem ao menos 1 registro com STATUS 'Concluído')
    dividido pelo (# JIRAs únicos que chegaram)
    """
    if mask is None:
        mask = pd.Series([True]*len(df), index=df.index)
    sub = df.loc[mask].copy()

    # limpar JIRA vazio
    jiras = sub["JIRA"].replace("", pd.NA).dropna()
    num_jiras = jiras.nunique()
    if num_jiras == 0:
        return np.nan

    # JIRAs que possuem ao menos um registro concluído
    concl_mask = sub["STATUS"].str.lower().str.startswith("concl")
    jiras_concluidos = sub.loc[concl_mask, "JIRA"].replace("", pd.NA).dropna().unique()
    num_jiras_concluidos = len(jiras_concluidos)

    return round(num_jiras_concluidos / num_jiras, 4)  # retorna razão (ex.: 0.75)


def kpi_pct_reprocesso_questionamento(df: pd.DataFrame, mask=None):
    """
    % de Questionamentos que viram reprocesso:
    total FLAG_REPROCESSO sobre registros onde TIPO == 'Questionamento'
    """
    if mask is None:
        mask = pd.Series([True]*len(df), index=df.index)
    sub = df.loc[mask]
    quests = sub[sub["TIPO"].str.lower() == "questionamento"]
    total_q = len(quests)
    if total_q == 0:
        return np.nan
    reproc = quests["FLAG_REPROCESSO"].sum()
    return round(reproc / total_q, 4)

def kpi_total_solicitacoes(df: pd.DataFrame, mask=None):
    if mask is None:
        return len(df)
    return int(mask.sum())

def gerar_resumo_kpis(df: pd.DataFrame, mask=None):
    """
    Gera um dicionário com todos os KPIs calculados.
    """
    return {
        "SLA_MÉDIO_DIAS_UTEIS": kpi_sla_medio(df, mask),
        "TAXA_RESOLUCAO_1_DEV": kpi_taxa_resolucao_1_dev(df, mask),
        "PCT_REPROCESSO_QUESTIONAMENTO": kpi_pct_reprocesso_questionamento(df, mask),
        "TOTAL_SOLICITACOES": kpi_total_solicitacoes(df, mask)
    }
