"""
processar_solicitacoes.py
Módulo responsável por:
- Padronizar colunas (tratar espaços, pontos, maiúsculas)
- Converter datas
- Calcular SLA (dias úteis)
- Criar flags usadas pelos KPIs (resolução 1ª, reprocesso)
Recebe um DataFrame (lido pelo app) e retorna o DataFrame tratado.
"""

import pandas as pd
import numpy as np
import unicodedata

def calcular_dias_uteis(start, end):
    try:
        if pd.isna(start) or pd.isna(end):
            return np.nan
        s = pd.to_datetime(start).date()
        e = pd.to_datetime(end).date()
        # np.busday_count conta dias úteis ENTRE start e end (exclui o end),
        # se quiser incluir o dia final, some 1 quando ambos forem dias úteis.
        n = np.busday_count(s, e)
        # incluir dia de conclusão se for dia útil (opcional) — manter sem incluir para consistência
        return int(n) if not pd.isna(n) else np.nan
    except Exception:
        return np.nan

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza os nomes das colunas:
    - remove acentos
    - substitui pontos e espaços por underscore
    - converte para MAIÚSCULAS
    - aplica mapa de variantes para nomes canônicos
    """
    df = df.copy()

    def _remove_acentos(texto):
        if not isinstance(texto, str):
            return texto
        texto_norm = unicodedata.normalize('NFKD', texto)
        texto_ascii = texto_norm.encode('ascii', 'ignore').decode('utf-8')
        return texto_ascii

    newcols = []
    for c in df.columns:
        c_clean = _remove_acentos(str(c)).strip()
        c_clean = c_clean.replace(".", "_").replace(" ", "_")
        # remover underscores duplicados
        while "__" in c_clean:
            c_clean = c_clean.replace("__", "_")
        c_clean = c_clean.upper()
        newcols.append(c_clean)

    df.columns = newcols

    rename_map = {
        # responsáveis
        "RESP_BU": "RESP_BU",
        "RESP_SM": "RESP_SM",
        "RESP__SM": "RESP_SM",  # novo caso corrigido
        "RESP__BU": "RESP_BU",  # idem, caso venha com duplo underscore

        # datas
        "DATA_SOLICITACAO": "DATA_SOLICITACAO",
        "DATA_ABERTURA": "DATA_ABERTURA",
        "DATA_CONCLUSAO": "DATA_CONCLUSAO",

        # detalhe / texto
        "DETALHE": "DETALHE_QUESTIONAMENTO",
        "DETALHE_QUESTIONAMENTO": "DETALHE_QUESTIONAMENTO",

        # quantidades
        "QTIA_QUEST": "QTDE_QUEST",
        "QTDE_QUEST": "QTDE_QUEST",
        "QTIA_QUEST_JIRA": "QTDE_QUEST_JIRA",
        "QTDE_QUEST_JIRA": "QTDE_QUEST_JIRA",

        # outros
        "OBSERVACOES": "OBSERVACOES",
        "STATUS": "STATUS",
        "TIPO": "TIPO",
        "CLIENTE": "CLIENTE",
        "CATEGORIA": "CATEGORIA",
        "JIRA": "JIRA",
        "CONCLUSAO_QUALITATIVA": "CONCLUSAO_QUALITATIVA",
    }

    df.rename(columns={c: rename_map.get(c, c) for c in df.columns}, inplace=True)
    return df


def processar_solicitacoes(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Pipeline principal:
    - Normaliza colunas
    - Garante existência das colunas essenciais (cria vazias se não houver)
    - Converte datas
    - Calcula SLA_DIAS_UTEIS (apenas para STATUS = 'Concluído')
    - Cria flags:
        FLAG_RESOLUCAO_1_DEV (1 se STATUS == 'Concluído' else 0)
        FLAG_REPROCESSO (1 se texto 'reprocesso' aparecer em conclusão qualitativa)
    Retorna df_tratado.
    """
    df = _normalize_columns(df_raw)

    # colunas esperadas (canônicas) - se faltarem criamos com NaN
    expected = [
        "BU", "RESP_BU", "DATA_SOLICITACAO", "CLIENTE", "CATEGORIA",
        "DETALHE_QUESTIONAMENTO", "TIPO", "RESP_SM",
        "QTDE_QUEST", "JIRA", "QTDE_QUEST_JIRA",
        "DATA_ABERTURA", "DATA_CONCLUSAO",
        "OBSERVACOES", "STATUS", "CONCLUSAO_QUALITATIVA"
    ]
    for col in expected:
        if col not in df.columns:
            df[col] = np.nan  # cria coluna vazia quando não existir

    # Algumas pessoas usam "DATA_SOLICITAÇÃO" com acento; já normalizamos mas garantimos ambas:
    # Converter datas (try multiple col names if present)
    for date_col in ["DATA_SOLICITACAO", "DATA_ABERTURA", "DATA_CONCLUSAO"]:
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')

    # NORMALIZAR STATUS (ex.: espaços/maiúsculas)
    df["STATUS"] = df["STATUS"].astype(str).str.strip().str.lower()
    # padronizar TIPO e BU também por segurança
    df["TIPO"] = df["TIPO"].astype(str).str.strip()
    df["BU"] = df["BU"].astype(str).str.strip()

    # SLA em dias úteis: usar DATA_SOLICITACAO -> DATA_CONCLUSAO quando STATUS == Concluído
    df["SLA_DIAS_UTEIS"] = df.apply(
        lambda r: calcular_dias_uteis(r.get("DATA_SOLICITACAO"), r.get("DATA_CONCLUSAO"))
        if isinstance(r.get("STATUS"), str) and r.get("STATUS").startswith("concl") else np.nan,
        axis=1
    )
    # Garantir tipo numérico
    df["SLA_DIAS_UTEIS"] = pd.to_numeric(df["SLA_DIAS_UTEIS"], errors="coerce")

    # Flags
    df["FLAG_RESOLUCAO_1_DEV"] = np.where(df["STATUS"].str.lower().str.startswith("concl"), 1, 0)

    # Busca por 'reprocesso' (insensível a caixa)
    df["FLAG_REPROCESSO"] = df["CONCLUSAO_QUALITATIVA"].astype(str).str.contains("reprocesso", case=False, na=False).astype(int)

    # Ajustes finais: garantir tipos razoáveis
    # JIRA para string
    df["JIRA"] = df["JIRA"].astype(str).replace("nan", "")
    # QTDE colunas para numérico quando possível
    for q in ["QTDE_QUEST", "QTDE_QUEST_JIRA"]:
        df[q] = pd.to_numeric(df[q], errors='coerce')

    # Reordenar colunas numa ordem clara (opcional)
    cols_order = expected + ["SLA_DIAS_UTEIS", "FLAG_RESOLUCAO_1_DEV", "FLAG_REPROCESSO"]
    cols_final = [c for c in cols_order if c in df.columns]
    df = df[cols_final]

    return df
