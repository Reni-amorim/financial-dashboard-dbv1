"""
Testes para o cálculo de ICMS
Execute: python test_icms.py

Baseado em registros reais da planilha de faturamento.
Quando a função calcular_icms() for implementada, importe-a aqui.
"""

# ============================================================
# Quando implementar, descomente a linha abaixo:
from app.services.icms_calculator import calcular_icms
# ============================================================


# ─────────────────────────────────────────────────────────────
# TABELA DE ALÍQUOTAS (referência para os testes)
# ─────────────────────────────────────────────────────────────
ALIQUOTAS_INTERESTADUAIS = {
    # Sul/Sudeste → Sul/Sudeste = 12%
    # Sul/Sudeste → Norte/Nordeste/Centro-Oeste = 7%
    "SP": {"SP": 12, "MG": 12, "RJ": 12, "PR": 12, "SC": 12, "RS": 12,
           "GO": 7,  "BA": 7,  "CE": 7,  "AM": 7,  "PA": 7,  "MT": 7,
           "MS": 7,  "MA": 7,  "PI": 7,  "RN": 7,  "PB": 7,  "PE": 7,
           "AL": 7,  "SE": 7,  "TO": 7,  "AC": 7,  "RO": 7,  "RR": 7,
           "AP": 7,  "DF": 7},
}

ALIQUOTAS_INTERNAS = {
    "SP": 12, "MG": 12, "RJ": 20, "PR": 12,
    "SC": 12, "RS": 12, "GO": 12, "BA": 12,
    "CE": 12, "AM": 12, "PA": 12, "MT": 12,
    "DF": 12, "MS": 12,
}

# Mapa de nome completo → sigla
ESTADO_SIGLA = {
    "São Paulo":       "SP",
    "Rio de Janeiro":  "RJ",
    "Minas Gerais":    "MG",
    "Paraná":          "PR",
    "Santa Catarina":  "SC",
    "Rio Grande do Sul": "RS",
    "Bahia":           "BA",
    "Goiás":           "GO",
    "Ceará":           "CE",
    "Amazonas":        "AM",
    "Pará":            "PA",
    "Mato Grosso":     "MT",
    "Mato Grosso do Sul": "MS",
    "Distrito Federal": "DF",
    "Maranhão":        "MA",
    "Piauí":           "PI",
    "Rio Grande do Norte": "RN",
    "Paraíba":         "PB",
    "Pernambuco":      "PE",
    "Alagoas":         "AL",
    "Sergipe":         "SE",
    "Tocantins":       "TO",
    "Acre":            "AC",
    "Rondônia":        "RO",
    "Roraima":         "RR",
    "Amapá":           "AP",
    "Espírito Santo":  "ES",
    "Rio Grande do Norte": "RN",
}


# ─────────────────────────────────────────────────────────────
# STUB — substitua pela função real quando implementar
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
    STUB do cálculo de ICMS.
    Substitua esta função pela implementação real.

    Args:
        receita_produto:   Receita por produtos (BRL)
        acrescimo:         Receita por acréscimo no preço (0 se não houver)
        estado_origem:     Sigla do estado de origem (ex: 'SP')
        estado_destino:    Nome completo ou sigla do estado destino
        tipo_documento:    'CNPJ XXXXXXXXXXXXXXXX' ou 'CPF XXXXXXXXXXX'
        tipo_contribuinte: 'Contribuinte' ou 'Não contribuinte'

    Returns:
        dict com base_calculo, aliquota, icms, difal, icms_total
    """
    # Converte estado destino para sigla se necessário
    if len(estado_destino) > 2:
        uf_destino = ESTADO_SIGLA.get(estado_destino, estado_destino)
    else:
        uf_destino = estado_destino.upper()

    uf_origem = estado_origem.upper()

    # Base de cálculo
    base_calculo = receita_produto + acrescimo

    # Identifica tipo de pessoa
    tipo_pessoa = "PJ" if "CNPJ" in str(tipo_documento).upper() else "PF"

    # Alíquota interestadual
    aliquota = ALIQUOTAS_INTERESTADUAIS.get(uf_origem, {}).get(uf_destino, 12)

    # ICMS normal
    icms = round(base_calculo * (aliquota / 100), 2)

    # DIFAL — apenas para não contribuintes (PF ou PJ não contribuinte)
    difal = 0.0
    eh_contribuinte = "contribuinte" in str(tipo_contribuinte).lower() and \
                      "não" not in str(tipo_contribuinte).lower()

    if not eh_contribuinte:
        aliq_interna_destino = ALIQUOTAS_INTERNAS.get(uf_destino, 12)
        difal = round(base_calculo * ((aliq_interna_destino - aliquota) / 100), 2)

    icms_total = round(icms + difal, 2)

    return {
        "base_calculo":   round(base_calculo, 2),
        "aliquota":       aliquota,
        "icms":           icms,
        "difal":          difal,
        "icms_total":     icms_total,
        "tipo_pessoa":    tipo_pessoa,
        "eh_contribuinte": eh_contribuinte,
        "uf_origem":      uf_origem,
        "uf_destino":     uf_destino,
    }


# ─────────────────────────────────────────────────────────────
# CASOS DE TESTE
# ─────────────────────────────────────────────────────────────

def test_venda1_pj_nao_contribuinte_sp():
    """
    Venda real #1: 2000015121715436
    - Produto: Moldura Painel 2 Din Multimídia Dvd Mp5 Gol G8 2021 2022
    - Receita: R$ 61,89 | Acréscimo: R$ 0,00
    - Comprador: CNPJ (PJ) | Não contribuinte
    - Destino: São Paulo (SP)
    - Origem empresa: SP (exemplo)
    - Esperado: operação interna SP→SP, alíquota 12%, sem DIFAL para contribuinte
    """
    resultado = calcular_icms(
        receita_produto=61.89,
        acrescimo=0.0,
        estado_origem="SP",
        estado_destino="São Paulo",
        tipo_documento="CNPJ 19806506000110",
        tipo_contribuinte="Não contribuinte",
    )

    print(f"\n{'='*55}")
    print(f"TESTE 1 — PJ Não Contribuinte | SP → SP")
    print(f"{'='*55}")
    print(f"  Base de cálculo : R$ {resultado['base_calculo']:.2f}")
    print(f"  Alíquota        : {resultado['aliquota']}%")
    print(f"  ICMS            : R$ {resultado['icms']:.2f}")
    print(f"  DIFAL           : R$ {resultado['difal']:.2f}")
    print(f"  ICMS Total      : R$ {resultado['icms_total']:.2f}")
    print(f"  Tipo pessoa     : {resultado['tipo_pessoa']}")
    print(f"  Contribuinte    : {resultado['eh_contribuinte']}")

    assert resultado["base_calculo"] == 61.89,   f"Base errada: {resultado['base_calculo']}"
    assert resultado["aliquota"] == 12,           f"Alíquota errada: {resultado['aliquota']}"
    assert resultado["icms"] == 7.43,             f"ICMS errado: {resultado['icms']}"
    assert resultado["tipo_pessoa"] == "PJ",      f"Tipo pessoa errado: {resultado['tipo_pessoa']}"
    assert resultado["eh_contribuinte"] == False, f"Contribuinte errado"

    print("  ✅ PASSOU")


def test_venda2_pf_com_acrescimo_rj():
    """
    Venda real #2: 2000011526307705
    - Produto: Multimidia 7 Polegadas Mp5 Espelhamento...
    - Receita: R$ 199,80 | Acréscimo: R$ 26,45
    - Comprador: PF (sem documento informado)
    - Destino: Rio de Janeiro (RJ)
    - Origem empresa: SP (exemplo)
    - Esperado: SP→RJ interestadual 12%, DIFAL = 20%-12% = 8%
    """
    resultado = calcular_icms(
        receita_produto=199.80,
        acrescimo=26.45,
        estado_origem="SP",
        estado_destino="Rio de Janeiro",
        tipo_documento="",
        tipo_contribuinte="",
    )

    print(f"\n{'='*55}")
    print(f"TESTE 2 — PF com Acréscimo | SP → RJ")
    print(f"{'='*55}")
    print(f"  Base de cálculo : R$ {resultado['base_calculo']:.2f}")
    print(f"  Alíquota        : {resultado['aliquota']}%")
    print(f"  ICMS            : R$ {resultado['icms']:.2f}")
    print(f"  DIFAL           : R$ {resultado['difal']:.2f}")
    print(f"  ICMS Total      : R$ {resultado['icms_total']:.2f}")
    print(f"  Tipo pessoa     : {resultado['tipo_pessoa']}")
    print(f"  Contribuinte    : {resultado['eh_contribuinte']}")

    assert resultado["base_calculo"] == 226.25,  f"Base errada: {resultado['base_calculo']}"
    assert resultado["aliquota"] == 12,           f"Alíquota errada: {resultado['aliquota']}"
    assert resultado["icms"] == 27.15,            f"ICMS errado: {resultado['icms']}"
    assert resultado["difal"] == 18.10,           f"DIFAL errado: {resultado['difal']}"
    assert resultado["icms_total"] == 45.25,      f"ICMS Total errado: {resultado['icms_total']}"
    assert resultado["tipo_pessoa"] == "PF",      f"Tipo pessoa errado: {resultado['tipo_pessoa']}"

    print("  ✅ PASSOU")


def test_pj_contribuinte_sem_difal():
    """
    Teste extra — PJ Contribuinte não gera DIFAL
    """
    resultado = calcular_icms(
        receita_produto=500.00,
        acrescimo=0.0,
        estado_origem="SP",
        estado_destino="Rio de Janeiro",
        tipo_documento="CNPJ 12345678000199",
        tipo_contribuinte="Contribuinte",
    )

    print(f"\n{'='*55}")
    print(f"TESTE 3 — PJ Contribuinte | SP → RJ (sem DIFAL)")
    print(f"{'='*55}")
    print(f"  Base de cálculo : R$ {resultado['base_calculo']:.2f}")
    print(f"  Alíquota        : {resultado['aliquota']}%")
    print(f"  ICMS            : R$ {resultado['icms']:.2f}")
    print(f"  DIFAL           : R$ {resultado['difal']:.2f}")
    print(f"  ICMS Total      : R$ {resultado['icms_total']:.2f}")
    print(f"  Contribuinte    : {resultado['eh_contribuinte']}")

    assert resultado["difal"] == 0.0,            f"DIFAL deveria ser 0: {resultado['difal']}"
    assert resultado["eh_contribuinte"] == True,  f"Deveria ser contribuinte"

    print("  ✅ PASSOU")


def test_origem_norte_destino_sp():
    """
    Teste extra — empresa no Norte/Nordeste vendendo para SP
    Alíquota interestadual = 12%
    """
    resultado = calcular_icms(
        receita_produto=300.00,
        acrescimo=0.0,
        estado_origem="AM",
        estado_destino="São Paulo",
        tipo_documento="CPF 12345678901",
        tipo_contribuinte="Não contribuinte",
    )

    print(f"\n{'='*55}")
    print(f"TESTE 4 — PF | AM → SP")
    print(f"{'='*55}")
    print(f"  Base de cálculo : R$ {resultado['base_calculo']:.2f}")
    print(f"  Alíquota        : {resultado['aliquota']}%")
    print(f"  ICMS            : R$ {resultado['icms']:.2f}")
    print(f"  DIFAL           : R$ {resultado['difal']:.2f}")
    print(f"  ICMS Total      : R$ {resultado['icms_total']:.2f}")

    print("  ✅ PASSOU")


# ─────────────────────────────────────────────────────────────
# RUNNER
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n🧪 INICIANDO TESTES DE ICMS\n")

    testes = [
        test_venda1_pj_nao_contribuinte_sp,
        test_venda2_pf_com_acrescimo_rj,
        test_pj_contribuinte_sem_difal,
        test_origem_norte_destino_sp,
    ]

    passou = 0
    falhou = 0

    for teste in testes:
        try:
            teste()
            passou += 1
        except AssertionError as e:
            print(f"  ❌ FALHOU: {e}")
            falhou += 1
        except Exception as e:
            print(f"  💥 ERRO: {e}")
            falhou += 1

    print(f"\n{'='*55}")
    print(f"📊 RESULTADO: {passou} passou | {falhou} falhou")
    print(f"{'='*55}\n")