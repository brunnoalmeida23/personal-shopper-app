import { buscarProdutos, criarCliente, criarPedido, gerarPix } from './api.js';
import { adicionarAoCarrinho, getCarrinho, limparCarrinho } from './cart.js';

let clienteId = null;

// Login
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

// Buscar produtos
document.getElementById('busca')?.addEventListener('input', (e) => {
    carregarProdutos(e.target.value);
});

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

// Função global para adicionar produto
window.adicionarProduto = (id, nome, preco) => {
    adicionarAoCarrinho({ id, nome, preco });
};

// Finalizar pedido
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
    
    const total = carrinho.reduce((sum, item) => sum + item.preco * item.quantidade, 0);
    
    try {
        const pedido = await criarPedido({
            cliente_id: clienteId,
            itens: itens,
            agendamento: 'manha',
            data_agendada: new Date().toISOString().split('T')[0]
        });
        
        const pagamento = await gerarPix(pedido.pedido_id);
        
        alert(`Pedido #${pedido.pedido_id.slice(0, 8)} criado! Total: R$ ${total.toFixed(2)}`);
        
        // Exibe QR Code PIX
        if (pagamento.qr_code_image) {
            const win = window.open('', '_blank');
            win.document.write(`
                <h1>Pague com PIX</h1>
                <img src="data:image/png;base64,${pagamento.qr_code_image}" />
                <p>Código: ${pagamento.qr_code}</p>
                <p>Vencimento: ${pagamento.expiration}</p>
            `);
        }
        
        limparCarrinho();
    } catch (error) {
        console.error('Erro ao criar pedido:', error);
        alert('Erro ao criar pedido. Tente novamente.');
    }
});
