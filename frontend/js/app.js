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
        console.log('🔄 Criando pedido...');
        const pedido = await criarPedido({
            cliente_id: clienteId,
            itens: itens,
            agendamento: 'manha',
            data_agendada: new Date().toISOString().split('T')[0]
        });

        console.log('✅ Pedido criado:', pedido);
        alert(`Pedido #${pedido.pedido_id.slice(0, 8)} criado! Total: R$ ${pedido.total.toFixed(2)}`);

        console.log('🔄 Gerando PIX para pedido:', pedido.pedido_id);
        const pagamento = await gerarPix(pedido.pedido_id);
        console.log('✅ Resposta do PIX:', pagamento);

        if (pagamento && pagamento.qr_code_image) {
            console.log('🎉 QR Code gerado com sucesso!');
            exibirQrCode(pagamento, pedido);
        } else if (pagamento && pagamento.error) {
            console.error('❌ Erro do Asaas:', pagamento.error);
            alert('Erro ao gerar PIX: ' + pagamento.error);
        } else {
            console.error('❌ QR Code não gerado. Resposta:', pagamento);
            alert('Erro ao gerar PIX. Tente novamente.');
        }

        limparCarrinho();
    } catch (error) {
        console.error('❌ Erro ao criar pedido:', error);
        alert('Erro ao criar pedido. Tente novamente.');
    }
});

// ==================== EXIBIR QR CODE ====================
function exibirQrCode(pagamento, pedido) {
    const container = document.createElement('div');
    container.id = 'pix-container';
    container.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.7);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
    `;
    
    container.innerHTML = `
        <div style="
            background: white;
            padding: 30px;
            border-radius: 16px;
            max-width: 400px;
            width: 90%;
            text-align: center;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            max-height: 90vh;
            overflow-y: auto;
        ">
            <h2 style="color: #2E7D32;">💰 Pague com PIX</h2>
            <p><strong>Pedido #${pedido.pedido_id.slice(0, 8)}</strong></p>
            <p style="font-size: 24px; font-weight: bold; color: #2E7D32;">
                R$ ${pedido.total.toFixed(2)}
            </p>
            <div style="margin: 20px 0;">
                <img src="data:image/png;base64,${pagamento.qr_code_image}" 
                     style="max-width: 250px; border: 2px solid #e0e0e0; border-radius: 8px; padding: 10px;" />
            </div>
            <p style="font-size: 14px; color: #555;">
                <strong>QR Code PIX</strong>
            </p>
            <p style="font-size: 12px; color: #888; margin-top: -10px;">
                ⏳ Expira em: ${pagamento.expiration || '24 horas'}
            </p>
            <div style="margin: 15px 0;">
                <button onclick="window.copiarPix()" style="
                    padding: 12px 24px;
                    background: #2E7D32;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    cursor: pointer;
                    font-size: 16px;
                    width: 100%;
                ">📋 Copiar código PIX</button>
            </div>
            <div style="
                background: #f5f5f5;
                padding: 12px;
                border-radius: 8px;
                font-size: 11px;
                word-break: break-all;
                font-family: monospace;
                max-height: 80px;
                overflow-y: auto;
                text-align: left;
                margin-bottom: 15px;
            " id="codigo-pix">${pagamento.qr_code || 'Código não disponível'}</div>
            <button onclick="document.getElementById('pix-container').remove()" style="
                padding: 12px 24px;
                background: #ccc;
                color: #333;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 16px;
                width: 100%;
            ">Fechar</button>
            <p style="font-size: 11px; color: #999; margin-top: 10px;">
                Após o pagamento, seu pedido será processado.
            </p>
        </div>
    `;
    
    document.body.appendChild(container);
    
    // Função global para copiar o código PIX
    window.copiarPix = function() {
        const texto = document.getElementById('codigo-pix').innerText;
        if (!texto || texto === 'Código não disponível') {
            alert('Código PIX não disponível para copiar.');
            return;
        }
        navigator.clipboard.writeText(texto).then(() => {
            alert('✅ Código PIX copiado com sucesso!');
        }).catch(() => {
            // Fallback para navegadores que não suportam clipboard
            const textarea = document.createElement('textarea');
            textarea.value = texto;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            alert('✅ Código PIX copiado com sucesso!');
        });
    };
}
