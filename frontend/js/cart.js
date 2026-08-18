// Gerenciamento do carrinho
let carrinho = [];

export function adicionarAoCarrinho(produto) {
    const existente = carrinho.find(item => item.id === produto.id);
    if (existente) {
        existente.quantidade += 1;
    } else {
        carrinho.push({ ...produto, quantidade: 1 });
    }
    atualizarCarrinho();
}

export function getCarrinho() {
    return carrinho;
}

export function limparCarrinho() {
    carrinho = [];
    atualizarCarrinho();
}

function atualizarCarrinho() {
    const container = document.getElementById('carrinho-itens');
    const totalElement = document.getElementById('carrinho-total');
    
    if (!container) return;
    
    if (carrinho.length === 0) {
        container.innerHTML = '<p>Seu carrinho está vazio</p>';
        if (totalElement) totalElement.textContent = 'Total: R$ 0,00';
        return;
    }
    
    let html = '';
    let total = 0;
    
    carrinho.forEach(item => {
        const subtotal = item.preco * item.quantidade;
        total += subtotal;
        html += `
            <div class="carrinho-item">
                <span>${item.nome} x ${item.quantidade}</span>
                <span>R$ ${subtotal.toFixed(2)}</span>
            </div>
        `;
    });
    
    container.innerHTML = html;
    if (totalElement) {
        totalElement.textContent = `Total: R$ ${total.toFixed(2)}`;
    }
}
