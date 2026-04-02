"""
Calculador de ICMS para vendas do Mercado Livre
Suporta operações internas, interestaduais e DIFAL
"""

# ─────────────────────────────────────────────────────────────
# TABELAS DE ALÍQUOTAS
# ─────────────────────────────────────────────────────────────

# Alíquotas interestaduais por estado de origem → destino
# Sul/Sudeste → Sul/Sudeste = 12%
# Sul/Sudeste → Norte/Nordeste/Centro-Oeste = 7%
# Norte/Nordeste/Centro-Oeste → qualquer = 12%
ALIQUOTAS_INTERESTADUAIS = {
    "SP": {"SP": 12, "MG": 12, "RJ": 12, "PR": 12, "SC": 12, "RS": 12, "ES": 12,
           "GO":  7, "BA":  7, "CE":  7, "AM":  7, "PA":  7, "MT":  7, "MS":  7,
           "MA":  7, "PI":  7, "RN":  7, "PB":  7, "PE":  7, "AL":  7, "SE":  7,
           "TO":  7, "AC":  7, "RO":  7, "RR":  7, "AP":  7, "DF":  7},
    "MG": {"SP": 12, "MG": 12, "RJ": 12, "PR": 12, "SC": 12, "RS": 12, "ES": 12,
           "GO":  7, "BA":  7, "CE":  7, "AM":  7, "PA":  7, "MT":  7, "MS":  7,
           "MA":  7, "PI":  7, "RN":  7, "PB":  7, "PE":  7, "AL":  7, "SE":  7,
           "TO":  7, "AC":  7, "RO":  7, "RR":  7, "AP":  7, "DF":  7},
    "RJ": {"SP": 12, "MG": 12, "RJ": 12, "PR": 12, "SC": 12, "RS": 12, "ES": 12,
           "GO":  7, "BA":  7, "CE":  7, "AM":  7, "PA":  7, "MT":  7, "MS":  7,
           "MA":  7, "PI":  7, "RN":  7, "PB":  7, "PE":  7, "AL":  7, "SE":  7,
           "TO":  7, "AC":  7, "RO":  7, "RR":  7, "AP":  7, "DF":  7},
    "PR": {"SP": 12, "MG": 12, "RJ": 12, "PR": 12, "SC": 12, "RS": 12, "ES": 12,
           "GO":  7, "BA":  7, "CE":  7, "AM":  7, "PA":  7, "MT":  7, "MS":  7,
           "MA":  7, "PI":  7, "RN":  7, "PB":  7, "PE":  7, "AL":  7, "SE":  7,
           "TO":  7, "AC":  7, "RO":  7, "RR":  7, "AP":  7, "DF":  7},
    "SC": {"SP": 12, "MG": 12, "RJ": 12, "PR": 12, "SC": 12, "RS": 12, "ES": 12,
           "GO":  7, "BA":  7, "CE":  7, "AM":  7, "PA":  7, "MT":  7, "MS":  7,
           "MA":  7, "PI":  7, "RN":  7, "PB":  7, "PE":  7, "AL":  7, "SE":  7,
           "TO":  7, "AC":  7, "RO":  7, "RR":  7, "AP":  7, "DF":  7},
    "RS": {"SP": 12, "MG": 12, "RJ": 12, "PR": 12, "SC": 12, "RS": 12, "ES": 12,
           "GO":  7, "BA":  7, "CE":  7, "AM":  7, "PA":  7, "MT":  7, "MS":  7,
           "MA":  7, "PI":  7, "RN":  7, "PB":  7, "PE":  7, "AL":  7, "SE":  7,
           "TO":  7, "AC":  7, "RO":  7, "RR":  7, "AP":  7, "DF":  7},
    "ES": {"SP": 12, "MG": 12, "RJ": 12, "PR": 12, "SC": 12, "RS": 12, "ES": 12,
           "GO":  7, "BA":  7, "CE":  7, "AM":  7, "PA":  7, "MT":  7, "MS":  7,
           "MA":  7, "PI":  7, "RN":  7, "PB":  7, "PE":  7, "AL":  7, "SE":  7,
           "TO":  7, "AC":  7, "RO":  7, "RR":  7, "AP":  7, "DF":  7},
    # Norte/Nordeste/Centro-Oeste → qualquer estado = 12%
    "GO": {uf: 12 for uf in ["SP","MG","RJ","PR","SC","RS","ES","GO","BA","CE",
                              "AM","PA","MT","MS","MA","PI","RN","PB","PE","AL",
                              "SE","TO","AC","RO","RR","AP","DF"]},
    "BA": {uf: 12 for uf in ["SP","MG","RJ","PR","SC","RS","ES","GO","BA","CE",
                              "AM","PA","MT","MS","MA","PI","RN","PB","PE","AL",
                              "SE","TO","AC","RO","RR","AP","DF"]},
    "CE": {uf: 12 for uf in ["SP","MG","RJ","PR","SC","RS","ES","GO","BA","CE",
                              "AM","PA","MT","MS","MA","PI","RN","PB","PE","AL",
                              "SE","TO","AC","RO","RR","AP","DF"]},
    "AM": {uf: 12 for uf in ["SP","MG","RJ","PR","SC","RS","ES","GO","BA","CE",
                              "AM","PA","MT","MS","MA","PI","RN","PB","PE","AL",
                              "SE","TO","AC","RO","RR","AP","DF"]},
    "PA": {uf: 12 for uf in ["SP","MG","RJ","PR","SC","RS","ES","GO","BA","CE",
                              "AM","PA","MT","MS","MA","PI","RN","PB","PE","AL",
                              "SE","TO","AC","RO","RR","AP","DF"]},
    "MT": {uf: 12 for uf in ["SP","MG","RJ","PR","SC","RS","ES","GO","BA","CE",
                              "AM","PA","MT","MS","MA","PI","RN","PB","PE","AL",
                              "SE","TO","AC","RO","RR","AP","DF"]},
    "MS": {uf: 12 for uf in ["SP","MG","RJ","PR","SC","RS","ES","GO","BA","CE",
                              "AM","PA","MT","MS","MA","PI","RN","PB","PE","AL",
                              "SE","TO","AC","RO","RR","AP","DF"]},
    "DF": {uf: 12 for uf in ["SP","MG","RJ","PR","SC","RS","ES","GO","BA","CE",
                              "AM","PA","MT","MS","MA","PI","RN","PB","PE","AL",
                              "SE","TO","AC","RO","RR","AP","DF"]},
}

# Alíquotas internas por estado (usadas para calcular o DIFAL)
ALIQUOTAS_INTERNAS = {
    "AC": 17, "AL": 12, "AP": 18, "AM": 20, "BA": 20,
    "CE": 20, "DF": 12, "ES": 17, "GO": 17, "MA": 22,
    "MT": 17, "MS": 17, "MG": 18, "PA": 17, "PB": 20,
    "PR": 12, "PE": 20, "PI": 21, "RJ": 20, "RN": 20,
    "RS": 12, "RO": 17, "RR": 20, "SC": 17, "SP": 12,
    "SE": 19, "TO": 20,
}

# Mapa de nome completo do estado → sigla
ESTADO_PARA_SIGLA = {
    "Acre": "AC", "Alagoas": "AL", "Amapá": "AP", "Amazonas": "AM",
    "Bahia": "BA", "Ceará": "CE", "Distrito Federal": "DF",
    "Espírito Santo": "ES", "Goiás": "GO", "Maranhão": "MA",
    "Mato Grosso": "MT", "Mato Grosso do Sul": "MS", "Minas Gerais": "MG",
    "Pará": "PA", "Paraíba": "PB", "Paraná": "PR", "Pernambuco": "PE",
    "Piauí": "PI", "Rio de Janeiro": "RJ", "Rio Grande do Norte": "RN",
    "Rio Grande do Sul": "RS", "Rondônia": "RO", "Roraima": "RR",
    "Santa Catarina": "SC", "São Paulo": "SP", "Sergipe": "SE",
    "Tocantins": "TO",
}


# ─────────────────────────────────────────────────────────────
# FUNÇÕES AUXILIARES
# ─────────────────────────────────────────────────────────────

def _normalizar_estado(estado: str) -> str:
    """
    Converte nome completo ou sigla para sigla em maiúsculo.
    Ex: 'São Paulo' → 'SP', 'sp' → 'SP'
    """
    estado = str(estado).strip()
    if len(estado) == 2:
        return estado.upper()
    return ESTADO_PARA_SIGLA.get(estado, estado.upper())


def _identificar_tipo_pessoa(tipo_documento: str) -> str:
    """
    Identifica se é PF ou PJ pelo documento.
    'CNPJ XXXXXXXXXXXXXXXX' → 'PJ'
    'CPF XXXXXXXXXXX'       → 'PF'
    Vazio ou desconhecido   → 'PF' (mais conservador para DIFAL)
    """
    doc = str(tipo_documento).strip().upper()
    if "CNPJ" in doc:
        return "PJ"
    return "PF"


def _eh_contribuinte(tipo_contribuinte: str) -> bool:
    """
    Retorna True apenas se for explicitamente 'Contribuinte'
    (sem a palavra 'não').
    """
    tc = str(tipo_contribuinte).strip().lower()
    return "contribuinte" in tc and "não" not in tc and "nao" not in tc


def _get_aliquota_interestadual(uf_origem: str, uf_destino: str) -> int:
    """
    Retorna a alíquota interestadual entre dois estados.
    Fallback: 12% se o estado de origem não estiver mapeado.
    """
    return ALIQUOTAS_INTERESTADUAIS.get(uf_origem, {}).get(uf_destino, 12)


def _get_aliquota_interna(uf: str) -> int:
    """
    Retorna a alíquota interna do estado.
    Fallback: 12%.
    """
    return ALIQUOTAS_INTERNAS.get(uf, 12)


# ─────────────────────────────────────────────────────────────
# FUNÇÃO PRINCIPAL
# ─────────────────────────────────────────────────────────────

def calcular_icms(
    receita_produto: float,
    acrescimo: float,
    estado_origem: str,
    estado_destino: str,
    tipo_documento: str,
    tipo_contribuinte: str,
) -> dict:
    """
    Calcula o ICMS estimado para uma venda do Mercado Livre.

    Args:
        receita_produto:   Receita por produtos (BRL)
        acrescimo:         Receita por acréscimo no preço (0 se não houver)
        estado_origem:     Sigla do estado de origem (ex: 'SP')
        estado_destino:    Nome completo ou sigla do estado destino
        tipo_documento:    'CNPJ XXXXXXXXXXXXXXXX' ou 'CPF XXXXXXXXXXX'
        tipo_contribuinte: 'Contribuinte' ou 'Não contribuinte'

    Returns:
        dict com:
            base_calculo   → receita_produto + acrescimo
            aliquota       → alíquota interestadual aplicada (%)
            icms           → ICMS normal (base × alíquota)
            difal          → DIFAL quando não contribuinte
            icms_total_venda     → icms + difal
            tipo_pessoa    → 'PF' ou 'PJ'
            eh_contribuinte→ True/False
            uf_origem      → sigla origem
            uf_destino     → sigla destino
    """
    # Normaliza estados
    uf_origem  = _normalizar_estado(estado_origem)
    uf_destino = _normalizar_estado(estado_destino)

    # Base de cálculo
    acrescimo_val = acrescimo if acrescimo and acrescimo == acrescimo else 0.0  # trata NaN
    base_calculo  = round(receita_produto + acrescimo_val, 2)

    # Identifica tipo de pessoa e contribuinte
    tipo_pessoa     = _identificar_tipo_pessoa(tipo_documento)
    contribuinte    = _eh_contribuinte(tipo_contribuinte)

    # Alíquota interestadual
    aliquota = _get_aliquota_interestadual(uf_origem, uf_destino)

    # ICMS normal
    icms = round(base_calculo * (aliquota / 100), 2)

    # DIFAL — apenas para não contribuintes
    difal = 0.0
    if not contribuinte:
        aliq_interna = _get_aliquota_interna(uf_destino)
        diferenca    = aliq_interna - aliquota
        if diferenca > 0:
            difal = round(base_calculo * (diferenca / 100), 2)

    icms_total_venda = round(icms + difal, 2)

    return {
        "base_calculo":    base_calculo,
        "aliquota":        aliquota,
        "icms":            icms,
        "difal":           difal,
        "icms_total_venda":      icms_total_venda,
        "tipo_pessoa":     tipo_pessoa,
        "eh_contribuinte": contribuinte,
        "uf_origem":       uf_origem,
        "uf_destino":      uf_destino,
    }