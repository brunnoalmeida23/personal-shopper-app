from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from .database import supabase
from .models import Cliente, Pedido, Pagamento, ItemPedido
from datetime import datetime, timedelta
import os
import requests

app = FastAPI(title="Personal Shopper Único API", version="1.0")

# CORS - Permite o frontend acessar
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, coloque o domínio do Vercel
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== ROTAS PÚBLICAS ====================

@app.get("/")
def root():
    return {"message": "Personal Shopper Único API", "version": "1.0"}

@app.get("/produtos")
def listar_produtos(busca: Optional[str] = None, categoria: Optional[str] = None):
    """Lista produtos do catálogo base com preço final (já com markup)"""
    query = supabase.table("produtos").select("*").eq("ativo", True)
    
    if busca:
        query = query.ilike("nome", f"%{busca}%")
    if categoria:
        query = query.eq("categoria", categoria)
    
    produtos = query.execute()
    
    # Calcula preço final com prioridade
    resultado = []
    for p in produtos.data:
        markup = p.get("markup", 1.03)
        
        if p.get("preco_atual"):
            preco_final = round(p["preco_atual"] * markup, 2)
            fonte = "manual"
        elif p.get("preco_carrefour"):
            preco_final = round(p["preco_carrefour"] * markup, 2)
            fonte = "carrefour"
        elif p.get("preco_atacadao"):
            preco_final = round(p["preco_atacadao"] * markup, 2)
            fonte = "atacadao"
        else:
            preco_final = round(p.get("preco_poupaki", 0) * markup, 2)
            fonte = "poupaki"
        
        resultado.append({
            **p,
            "preco_final": preco_final,
            "fonte": fonte
        })
    
    return resultado

@app.post("/cliente")
def criar_cliente(cliente: Cliente):
    """Cadastra um cliente (morador)"""
    # Verifica se já existe
    existente = supabase.table("clientes").select("*").eq("apartamento", cliente.apartamento).execute()
    if existente.data:
        return existente.data[0]
    
    # Cria novo
    novo = supabase.table("clientes").insert(cliente.dict()).execute()
    return novo.data[0]

@app.post("/pedido")
def criar_pedido(pedido: Pedido):
    """Cria um novo pedido"""
    # Calcula total
    total = sum([item.preco_unitario * item.quantidade for item in pedido.itens])
    
    # Insere pedido
    novo_pedido = supabase.table("pedidos").insert({
        "cliente_id": pedido.cliente_id,
        "total": total,
        "agendamento": pedido.agendamento,
        "data_agendada": pedido.data_agendada,
        "observacoes": pedido.observacoes,
        "status": "aberto"
    }).execute()
    
    pedido_id = novo_pedido.data[0]["id"]
    
    # Insere itens
    for item in pedido.itens:
        supabase.table("pedido_itens").insert({
            "pedido_id": pedido_id,
            "produto_id": item.produto_id,
            "nome_produto": item.nome_produto,
            "quantidade": item.quantidade,
            "preco_unitario": item.preco_unitario,
            "observacoes": item.observacoes
        }).execute()
    
    return {"pedido_id": pedido_id, "total": total, "status": "aberto"}

@app.get("/pedido/{pedido_id}")
def buscar_pedido(pedido_id: str):
    """Busca um pedido completo com itens"""
    pedido = supabase.table("pedidos").select("*, clientes(*)").eq("id", pedido_id).execute()
    if not pedido.data:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    
    itens = supabase.table("pedido_itens").select("*").eq("pedido_id", pedido_id).execute()
    
    return {
        **pedido.data[0],
        "itens": itens.data
    }

@app.get("/pedido/{pedido_id}/status")
def status_pedido(pedido_id: str):
    """Consulta status do pedido"""
    pedido = supabase.table("pedidos").select("status").eq("id", pedido_id).execute()
    if not pedido.data:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return {"status": pedido.data[0]["status"]}

# ==================== ROTAS DE PAGAMENTO (Asaas) ====================

ASAAS_API_KEY = os.environ.get("ASAAS_API_KEY")
ASAAS_URL = os.environ.get("ASAAS_URL", "https://sandbox.asaas.com/api/v3")

def criar_cliente_asaas(telefone: str, nome: str):
    """Cria ou busca cliente no Asaas"""
    headers = {
        "access_token": ASAAS_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Busca se já existe
    response = requests.get(f"{ASAAS_URL}/customers?phone={telefone}", headers=headers)
    if response.status_code == 200 and response.json().get("data"):
        return response.json()["data"][0]
    
    # Cria novo
    payload = {
        "name": nome,
        "phone": telefone,
        "email": f"{telefone}@temp.com"
    }
    response = requests.post(f"{ASAAS_URL}/customers", json=payload, headers=headers)
    return response.json()

@app.post("/pagamento/pix/{pedido_id}")
def gerar_pix(pedido_id: str):
    """Gera QR Code PIX para o pedido"""
    # Busca pedido
    pedido = supabase.table("pedidos").select("*, clientes(*)").eq("id", pedido_id).execute()
    if not pedido.data:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    
    p = pedido.data[0]
    cliente = p["clientes"]
    
    # Cria cliente no Asaas
    cliente_asaas = criar_cliente_asaas(cliente["telefone"], cliente["nome"])
    
    headers = {
        "access_token": ASAAS_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "customer": cliente_asaas["id"],
        "billingType": "PIX",
        "value": p["total"],
        "dueDate": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
        "description": f"Pedido {pedido_id[:8]} - {cliente['apartamento']}"
    }
    
    response = requests.post(f"{ASAAS_URL}/payments", json=payload, headers=headers)
    data = response.json()
    
    # Atualiza pedido
    supabase.table("pedidos").update({
        "pagamento_id": data.get("id"),
        "pagamento_tipo": "pix",
        "status": "aguardando_pagamento"
    }).eq("id", pedido_id).execute()
    
    return {
        "qr_code": data.get("pixQrCode"),
        "qr_code_image": data.get("encodedImage"),
        "expiration": data.get("expirationDate"),
        "payment_id": data.get("id")
    }

@app.post("/webhook/asaas")
async def webhook_asaas(request: Request):
    """Webhook para receber confirmação do Asaas"""
    payload = await request.json()
    
    payment_id = payload.get("payment", {}).get("id")
    status = payload.get("payment", {}).get("status")
    
    if status == "CONFIRMED" and payment_id:
        # Atualiza pedido
        pedido = supabase.table("pedidos").update({
            "status": "pago"
        }).eq("pagamento_id", payment_id).execute()
        
        if pedido.data:
            # Aqui você pode enviar notificação via WhatsApp
            print(f"✅ Pedido {payment_id} pago com sucesso!")
    
    return {"status": "ok"}

# ==================== ROTAS DE PRODUTOS SOB DEMANDA ====================

@app.post("/buscar-produto")
def buscar_produto(nome: str, cliente_id: Optional[str] = None):
    """Busca produto no catálogo base ou sob demanda"""
    # 1. Busca no catálogo base
    resultado = supabase.table("produtos").select("*").ilike("nome", f"%{nome}%").eq("ativo", True).execute()
    
    if resultado.data:
        p = resultado.data[0]
        markup = p.get("markup", 1.03)
        
        if p.get("preco_atual"):
            preco_final = p["preco_atual"] * markup
        elif p.get("preco_carrefour"):
            preco_final = p["preco_carrefour"] * markup
        else:
            preco_final = p.get("preco_poupaki", 0) * markup
        
        return {
            "encontrado": True,
            "produto": {
                "id": p["id"],
                "nome": p["nome"],
                "preco": round(preco_final, 2),
                "fonte": p.get("fonte", "manual"),
                "imagem": p.get("imagem")
            }
        }
    
    # 2. Fallback: produto não encontrado
    # Salva como solicitação
    if cliente_id:
        supabase.table("produtos_sob_demanda").insert({
            "nome_busca": nome,
            "cliente_id": cliente_id,
            "status": "solicitado"
        }).execute()
    
    return {
        "encontrado": False,
        "solicitar": True,
        "mensagem": "Produto não encontrado. Clique em 'Solicitar' para adicionarmos ao catálogo."
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
