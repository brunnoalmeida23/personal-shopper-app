from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from .database import supabase
from .models import Cliente, Pedido, Pagamento, ItemPedido
from datetime import datetime, timedelta
import os
import requests

app = FastAPI(title="Personal Shopper Único API", version="1.0")

# ==================== CORS ====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== FUNÇÃO AUXILIAR PARA TELEFONE ====================

def formatar_telefone_asaas(telefone: str) -> str:
    """
    Formata o telefone para o padrão exato do Asaas.
    Remove tudo que não é número, remove o 55 se existir,
    e garante que tenha 11 dígitos (DDD + 9 + 8 números).
    """
    # Remove tudo que não é número
    numero = ''.join(filter(str.isdigit, telefone))
    
    # Remove o 55 se estiver no início
    if numero.startswith("55"):
        numero = numero[2:]
    
    # Se tem 10 dígitos, adiciona o 9 após o DDD
    if len(numero) == 10:
        numero = numero[:2] + "9" + numero[2:]
    
    # Se tem mais de 11 dígitos, pega os últimos 11
    if len(numero) > 11:
        numero = numero[-11:]
    
    # Se tem menos de 10 dígitos, retorna vazio
    if len(numero) < 10:
        return ""
    
    return numero

# ==================== ROTAS ====================

@app.get("/")
def root():
    return {"message": "Personal Shopper Único API", "version": "1.0"}

@app.get("/produtos")
def listar_produtos(busca: Optional[str] = None, categoria: Optional[str] = None):
    query = supabase.table("produtos").select("*").eq("ativo", True)
    
    if busca:
        query = query.ilike("nome", f"%{busca}%")
    if categoria:
        query = query.eq("categoria", categoria)
    
    produtos = query.execute()
    
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
    # Verifica se já existe
    existente = supabase.table("clientes").select("*").eq("apartamento", cliente.apartamento).execute()
    if existente.data:
        return existente.data[0]
    
    # Cria novo cliente com CPF
    novo = supabase.table("clientes").insert({
        "apartamento": cliente.apartamento,
        "nome": cliente.nome,
        "telefone": cliente.telefone,
        "bloco": cliente.bloco,
        "cpf": cliente.cpf
    }).execute()
    
    print(f"✅ Cliente criado com CPF: {cliente.cpf}")
    return novo.data[0]

@app.post("/pedido")
def criar_pedido(pedido: Pedido):
    total = sum([item.preco_unitario * item.quantidade for item in pedido.itens])
    
    novo_pedido = supabase.table("pedidos").insert({
        "cliente_id": pedido.cliente_id,
        "total": total,
        "agendamento": pedido.agendamento,
        "data_agendada": pedido.data_agendada,
        "observacoes": pedido.observacoes,
        "status": "aberto"
    }).execute()
    
    pedido_id = novo_pedido.data[0]["id"]
    
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
    pedido = supabase.table("pedidos").select("status").eq("id", pedido_id).execute()
    if not pedido.data:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return {"status": pedido.data[0]["status"]}

# ==================== PAGAMENTO PIX (ASAAS) ====================

ASAAS_API_KEY = os.environ.get("ASAAS_API_KEY")
ASAAS_URL = os.environ.get("ASAAS_URL", "https://sandbox.asaas.com/api/v3")

@app.post("/pagamento/pix/{pedido_id}")
def gerar_pix(pedido_id: str):
    print(f"🔄 Gerando PIX para pedido: {pedido_id}")

    # Busca o pedido com os dados do cliente
    pedido = supabase.table("pedidos").select("*, clientes(*)").eq("id", pedido_id).execute()
    if not pedido.data:
        print(f"❌ Pedido {pedido_id} não encontrado")
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    p = pedido.data[0]
    cliente = p["clientes"]

    if not ASAAS_API_KEY:
        print("❌ ASAAS_API_KEY não configurada")
        return {"error": "Asaas não configurado", "status": "pending"}

    headers = {
        "access_token": ASAAS_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        # 1. Formata o telefone usando a função auxiliar
        telefone_formatado = formatar_telefone_asaas(cliente["telefone"])
        print(f"📱 Telefone formatado: {telefone_formatado} (len: {len(telefone_formatado)})")

        # 2. Busca ou cria cliente no Asaas com CPF
        cpf_cliente = cliente.get("cpf", "40589095870")
        print(f"📋 CPF do cliente: {cpf_cliente}")

        # Busca cliente por CPF
        search_url = f"{ASAAS_URL}/customers?cpfCnpj={cpf_cliente}"
        response = requests.get(search_url, headers=headers)

        if response.status_code == 200 and response.json().get("data"):
            customer_id = response.json()["data"][0]["id"]
            print(f"✅ Cliente encontrado no Asaas por CPF: {customer_id}")
        else:
            # Cria cliente no Asaas com CPF
            payload_cliente = {
                "name": cliente["nome"],
                "cpfCnpj": cpf_cliente
            }
            if telefone_formatado:
                payload_cliente["phone"] = telefone_formatado
            
            print(f"📦 Payload criação cliente: {payload_cliente}")
            response = requests.post(f"{ASAAS_URL}/customers", json=payload_cliente, headers=headers)
            print(f"📦 Resposta criação cliente: {response.status_code} - {response.text}")

            if response.status_code not in [200, 201]:
                return {"error": f"Erro ao criar cliente: {response.text}", "status": "error"}

            customer_id = response.json().get("id")
            print(f"✅ Cliente criado no Asaas: {customer_id}")

        # 3. Cria cobrança PIX com externalReference = pedido_id
        valor_formatado = f"{p['total']:.2f}".replace(",", ".")
        payload_pix = {
            "customer": customer_id,
            "billingType": "PIX",
            "value": valor_formatado,
            "dueDate": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
            "description": f"Pedido {pedido_id[:8]} - {cliente['apartamento']}",
            "externalReference": pedido_id  # <-- VINCULA O PAGAMENTO AO PEDIDO
        }

        print(f"📦 Payload PIX: {payload_pix}")
        response = requests.post(f"{ASAAS_URL}/payments", json=payload_pix, headers=headers)
        print(f"📦 Resposta PIX: {response.status_code} - {response.text}")

        if response.status_code not in [200, 201]:
            return {"error": f"Erro ao criar cobrança PIX: {response.text}", "status": "error"}

        data = response.json()

        # Atualiza o pedido com o ID da cobrança
        supabase.table("pedidos").update({
            "pagamento_id": data.get("id"),
            "pagamento_tipo": "pix",
            "status": "aguardando_pagamento"
        }).eq("id", pedido_id).execute()

        return {
            "qr_code": data.get("pixQrCode"),
            "qr_code_image": data.get("encodedImage"),
            "expiration": data.get("expirationDate"),
            "payment_id": data.get("id"),
            "pedido_id": pedido_id
        }

    except Exception as e:
        print(f"❌ Erro ao gerar PIX: {str(e)}")
        return {"error": str(e), "status": "error"}


# ==================== WEBHOOK ASAAS ====================

@app.post("/webhook/asaas")
async def webhook_asaas(request: Request):
    try:
        payload = await request.json()
        print(f"📨 Webhook recebido: {payload}")
        
        # Verifica se é uma confirmação de pagamento
        event_type = payload.get("event")
        
        if event_type == "PAYMENT_CONFIRMED":
            payment_data = payload.get("payment", {})
            payment_id = payment_data.get("id")
            external_reference = payment_data.get("externalReference")
            
            print(f"🔍 Payment ID: {payment_id}")
            print(f"🔍 External Reference (pedido_id): {external_reference}")
            
            if external_reference:
                # ATUALIZA O PEDIDO PARA "PAGO"
                result = supabase.table("pedidos").update({
                    "status": "pago",
                    "entregue_em": datetime.now().isoformat()
                }).eq("id", external_reference).execute()
                
                print(f"✅ Pedido {external_reference} foi pago!")
                print(f"📦 Resultado da atualização: {result}")
                
                # AQUI VOCÊ PODE ENVIAR NOTIFICAÇÃO
                # (WhatsApp, Telegram, email, etc.)
                # enviar_notificacao_whatsapp(external_reference)
                
                return {"status": "ok", "message": "Pedido atualizado com sucesso"}
            else:
                print("⚠️ External Reference não encontrado no payload")
                return {"status": "error", "message": "External Reference não encontrado"}
        
        # Outros eventos (PAYMENT_OVERDUE, PAYMENT_RECEIVED, etc.)
        print(f"📌 Evento recebido: {event_type}")
        return {"status": "ok", "message": f"Evento {event_type} recebido"}
        
    except Exception as e:
        print(f"❌ Erro no webhook: {str(e)}")
        return {"status": "error", "message": str(e)}


# ==================== ROTA DE TESTE ASAAS ====================

@app.get("/teste/asaas")
def teste_asaas():
    chave = os.environ.get("ASAAS_API_KEY")
    url = os.environ.get("ASAAS_URL")
    return {
        "chave_configurada": bool(chave),
        "chave_preview": chave[:20] + "..." if chave else "NÃO CONFIGURADA",
        "asaas_url": url if url else "NÃO CONFIGURADA",
        "servidor": "Render"
    }

@app.post("/buscar-produto")
def buscar_produto(nome: str, cliente_id: Optional[str] = None):
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
