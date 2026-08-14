from pydantic import BaseModel
from typing import Optional, List

class Cliente(BaseModel):
    apartamento: str
    nome: str
    telefone: str
    bloco: Optional[str] = None

class Produto(BaseModel):
    nome: str
    ean: Optional[str] = None
    categoria: Optional[str] = None
    preco_atual: Optional[float] = None
    preco_poupaki: Optional[float] = None
    markup: Optional[float] = 1.03

class ItemPedido(BaseModel):
    produto_id: Optional[str] = None
    nome_produto: str
    quantidade: int
    preco_unitario: float
    observacoes: Optional[str] = None

class Pedido(BaseModel):
    cliente_id: str
    itens: List[ItemPedido]
    agendamento: str
    data_agendada: str
    observacoes: Optional[str] = None

class Pagamento(BaseModel):
    pedido_id: str
    tipo: str
    parcelas: Optional[int] = 1
    dados_cartao: Optional[dict] = None
