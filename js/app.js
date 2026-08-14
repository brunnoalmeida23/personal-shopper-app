import { buscarProdutos, criarCliente, criarPedido, gerarPix } from './api.js';
import { adicionarAoCarrinho, getCarrinho, limparCarrinho } from './cart.js';

let clienteId = null;

// ==================== LOGIN ====================
document.getElementById('btn-login')?.addEventListener('click', async () => {
    const apartamento = document.getElementById('apartamento').value;
    const nome = document.getElementById('nome').value;
    const telefone = document.getElementById('telefone').value;
    
    if (!apartamento || !nome || !telefone) {
        alert('Preencha todos os campos');
        return;
    }
    
    try {
        const cliente = await criarCliente({ apartamento, nome, telefone });
        clienteId = cliente.id;
        
        document.getElementById('login').style.display = 'none';
        document.getElementById('produtos').style.display = 'block';
        
        carregarProdutos();
    } catch (error) {
        console.error('Erro no login:', error);
        alert('Erro ao fazer login. Tente novamente.');
    }
});

// ==================== BUSCA ====================
document.getElementById('busca')?.addEventListener('input', (e) => {
    carregarProdutos(e.target.value);
});

// ==================== CARREGAR PRODUTOS ====================
async function carregarProdutos(busca = '') {
    const container = document.getElementById('lista-produtos');
    container.innerHTML = 'Carregando...';
    
    try {
        const produtos = await buscarProdutos(busca);
        
        if (produtos.length === 0) {
            container.innerHTML = '<p>Nenhum produto encontrado</p>';
            return;
        }
        
        let html = '';
        produtos.forEach(p => {
            html += `
                <div class="produto-card">
                    <h4>${p.nome}</h4>
                    <div class="preco">R$ ${p.preco_final.toFixed(2)}</div>
                    <div class="fonte">Fonte: ${p.fonte}</div>
                    <button onclick="window.adicionarProduto('${p.id}', '${p.nome}', ${p.preco_final})">🛒 Adicionar</button>
                </div>
            `;
        });
        
        container.innerHTML = html;
    } catch (error) {
        console.error('Erro ao carregar produtos:', error);
        container.innerHTML = '<p>Erro ao carregar produtos. Tente novamente.</p>';
    }
}

// ==================== ADICIONAR PRODUTO ====================
window.adicionarProduto = (id, nome, preco) => {
    adicionarAoCarrinho({ id, nome, preco });
};

// ==================== FINALIZAR PEDIDO ====================
document.getElementById('btn-finalizar')?.addEventListener('click', async () => {
    const carrinho = getCarrinho();

    if (carrinho.length === 0) {
        alert('Seu carrinho está vazio!');
        return;
    }

    const itens = carrinho.map(item => ({
        produto_id: item.id,
        nome_produto: item.nome,
        quantidade: item.quantidade,
        preco_unitario: item.preco
    }));

    try {
        // 1. Cria o pedido
        const pedido = await criarPedido({
            cliente_id: clienteId,
            itens: itens,
            agendamento: 'manha',
            data_agendada: new Date().toISOString().split('T')[0]
        });

        alert(`Pedido #${pedido.pedido_id.slice(0, 8)} criado! Total: R$ ${pedido.total.toFixed(2)}`);

        // 2. Gera o PIX
        const pagamento = await gerarPix(pedido.pedido_id);

        // 3. Exibe o QR Code
        if (pagamento.qr_code_image) {
            // Abre uma nova janela com o QR Code
            const win = window.open('', '_blank', 'width=420,height=650');
            win.document.write(`
                <html>
                <head>
                    <title>Pagamento PIX</title>
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            text-align: center;
                            padding: 20px;
                            background: #f5f5f5;
                            margin: 0;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            min-height: 100vh;
                        }
                        .container {
                            background: white;
                            border-radius: 16px;
                            padding: 30px;
                            max-width: 400px;
                            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                        }
                        h2 {
                            color: #2E7D32;
                            margin-top: 0;
                        }
                        .total {
                            font-size: 24px;
                            font-weight: bold;
                            color: #2E7D32;
                            margin: 10px 0;
                        }
                        .qr-code {
                            margin: 20px 0;
                        }
                        .qr-code img {
                            max-width: 280px;
                            border: 2px solid #e0e0e0;
                            border-radius: 8px;
                            padding: 10px;
                            background: white;
                        }
                        .codigo {
                            font-size: 11px;
                            word-break: break-all;
                            background: #f0f0f0;
                            padding: 10px;
                            border-radius: 8px;
                            margin: 10px 0;
                            font-family: monospace;
                            max-height: 80px;
                            overflow-y: auto;
                        }
                        .btn-copiar {
                            padding: 12px 24px;
                            background: #2E7D32;
                            color: white;
                            border: none;
                            border-radius: 8px;
                            font-size: 16px;
                            cursor: pointer;
                            margin: 5px;
                        }
                        .btn-copiar:hover {
                            background: #1B5E20;
                        }
                        .btn-fechar {
                            padding: 12px 24px;
                            background: #ccc;
                            color: #333;
                            border: none;
                            border-radius: 8px;
                            font-size: 16px;
                            cursor: pointer;
                            margin: 5px;
                        }
                        .btn-fechar:hover {
                            background: #bbb;
                        }
                        .expira {
                            font-size: 12px;
                            color: #888;
                            margin-top: 10px;
                        }
                        .pedido-id {
                            font-size: 14px;
                            color: #555;
                        }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h2>💰 Pague com PIX</h2>
                        <div class="pedido-id">Pedido #${pedido.pedido_id.slice(0, 8)}</div>
                        <div class="total">R$ ${pedido.total.toFixed(2)}</div>
                        <div class="qr-code">
                            <img src="data:image/png;base64,${pagamento.qr_code_image}" alt="QR Code PIX" />
                        </div>
                        <p><strong>Código copia e cola:</strong></p>
                        <div class="codigo" id="codigo-pix">${pagamento.qr_code}</div>
                        <button class="btn-copiar" onclick="copiarPix()">📋 Copiar código</button>
                        <br>
                        <button class="btn-fechar" onclick="window.close()">Fechar</button>
                        <div class="expira">⏳ Expira em: ${pagamento.expiration || '24 horas'}</div>
                    </div>
                    <script>
                        function copiarPix() {
                            const texto = document.getElementById('codigo-pix').innerText;
                            navigator.clipboard.writeText(texto).then(() => {
                                alert('✅ Código PIX copiado!');
                            }).catch(() => {
                                // Fallback para navegadores mais antigos
                                const range = document.createRange();
                                range.selectNode(document.getElementById('codigo-pix'));
                                window.getSelection().removeAllRanges();
                                window.getSelection().addRange(range);
                                document.execCommand('copy');
                                alert('✅ Código PIX copiado!');
                            });
                        }
                    <\/script>
                </body>
                </html>
            `);
            win.document.close();
        } else {
            alert('Erro ao gerar PIX. Tente novamente.');
        }

        limparCarrinho();
    } catch (error) {
        console.error('Erro ao criar pedido:', error);
        alert('Erro ao criar pedido. Tente novamente.');
    }
});
