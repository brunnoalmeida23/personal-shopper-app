// Configuração da API
const API_URL = 'https://personal-shopper-app-ten.vercel.app';

export async function buscarProdutos(busca = '') {
    const url = busca ? `${API_URL}/produtos?busca=${busca}` : `${API_URL}/produtos`;
    const response = await fetch(url);
    return response.json();
}

export async function criarCliente(cliente) {
    const response = await fetch(`${API_URL}/cliente`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cliente)
    });
    return response.json();
}

export async function criarPedido(pedido) {
    const response = await fetch(`${API_URL}/pedido`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(pedido)
    });
    return response.json();
}

export async function gerarPix(pedidoId) {
    const response = await fetch(`${API_URL}/pagamento/pix/${pedidoId}`, {
        method: 'POST'
    });
    return response.json();
}
