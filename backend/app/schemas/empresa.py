"""
Schemas Pydantic para validação de Empresa
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


REGIMES_VALIDOS = ["Simples Nacional", "Lucro Presumido", "Lucro Real"]

ESTADOS_VALIDOS = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
    "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
    "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
]


def _formatar_cnpj(cnpj: str) -> str:
    """Remove formatação e retorna só números"""
    return "".join(filter(str.isdigit, cnpj))


class EmpresaCreate(BaseModel):
    nome:               str   = Field(min_length=2, max_length=255)
    cnpj:               str   = Field(min_length=14, max_length=18)
    estado:             str   = Field(min_length=2, max_length=2)
    regime_tributario:  str

    def model_post_init(self, __context):
        # Valida estado
        if self.estado.upper() not in ESTADOS_VALIDOS:
            raise ValueError(f"Estado inválido: {self.estado}")

        # Valida regime
        if self.regime_tributario not in REGIMES_VALIDOS:
            raise ValueError(f"Regime inválido: {self.regime_tributario}")

        # Valida CNPJ (apenas dígitos)
        cnpj_numeros = _formatar_cnpj(self.cnpj)
        if len(cnpj_numeros) != 14:
            raise ValueError("CNPJ deve ter 14 dígitos")


class EmpresaUpdate(BaseModel):
    nome:               Optional[str]  = Field(None, min_length=2, max_length=255)
    cnpj:               Optional[str]  = Field(None, min_length=14, max_length=18)
    estado:             Optional[str]  = Field(None, min_length=2, max_length=2)
    regime_tributario:  Optional[str]  = None


class EmpresaOut(BaseModel):
    id:                 int
    user_id:            int
    nome:               str
    cnpj:               str
    estado:             str
    regime_tributario:  str
    created_at:         datetime

    class Config:
        from_attributes = True