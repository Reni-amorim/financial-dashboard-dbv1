from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


REGIMES_VALIDOS = ["Simples Nacional", "Lucro Presumido", "Lucro Real"]

ESTADOS_VALIDOS = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
    "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
    "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
]


class CompanyCreate(BaseModel):
    name:              str = Field(min_length=2, max_length=255)
    document:          str = Field(min_length=14, max_length=18)
    state_origin:      str = Field(min_length=2, max_length=2)
    regime_tributario: str

    def model_post_init(self, __context):
        if self.state_origin.upper() not in ESTADOS_VALIDOS:
            raise ValueError(f"Estado inválido: {self.state_origin}")
        if self.regime_tributario not in REGIMES_VALIDOS:
            raise ValueError(f"Regime inválido: {self.regime_tributario}")
        if len("".join(filter(str.isdigit, self.document))) != 14:
            raise ValueError("CNPJ deve ter 14 dígitos")


class CompanyUpdate(BaseModel):
    name:              Optional[str] = Field(None, min_length=2, max_length=255)
    document:          Optional[str] = Field(None, min_length=14, max_length=18)
    state_origin:      Optional[str] = Field(None, min_length=2, max_length=2)
    regime_tributario: Optional[str] = None


class CompanyOut(BaseModel):
    id:                int
    user_id:           int
    name:              str
    document:          Optional[str]
    state_origin:      Optional[str]
    regime_tributario: Optional[str]
    created_at:        datetime

    class Config:
        from_attributes = True