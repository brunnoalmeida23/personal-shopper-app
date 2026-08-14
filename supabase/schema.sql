-- Tabela de clientes
CREATE TABLE clientes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    apartamento TEXT UNIQUE NOT NULL,
    nome TEXT NOT NULL,
    telefone TEXT NOT NULL,
    bloco TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE produtos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    nome TEXT NOT NULL,
    ean TEXT UNIQUE,
    categoria TEXT,
    descricao TEXT,
    imagem TEXT,
    preco_atual FLOAT,
    preco_poupaki FLOAT,
    preco_atacadao FLOAT,
    preco_carrefour FLOAT,
    fonte TEXT DEFAULT 'manual',
    ultima_atualizacao TIMESTAMP,
    ativo BOOLEAN DEFAULT TRUE,
    markup FLOAT DEFAULT 1.03
);

CREATE TABLE pedidos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    cliente_id UUID REFERENCES clientes(id),
    status TEXT DEFAULT 'aberto',
    total FLOAT,
    agendamento TEXT,
    data_agendada DATE,
    observacoes TEXT,
    pagamento_id TEXT,
    pagamento_tipo TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    entregue_em TIMESTAMP
);

CREATE TABLE pedido_itens (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    pedido_id UUID REFERENCES pedidos(id) ON DELETE CASCADE,
    produto_id UUID REFERENCES produtos(id),
    nome_produto TEXT NOT NULL,
    quantidade INT NOT NULL,
    preco_unitario FLOAT NOT NULL,
    observacoes TEXT
);

CREATE TABLE produtos_sob_demanda (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    nome_busca TEXT NOT NULL,
    preco_encontrado FLOAT,
    mercado TEXT,
    ean TEXT,
    imagem TEXT,
    cliente_id UUID REFERENCES clientes(id),
    status TEXT DEFAULT 'buscado',
    observacoes TEXT,
    data_busca TIMESTAMP DEFAULT NOW()
);

CREATE TABLE scraping_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    mercado TEXT NOT NULL,
    produtos_atualizados INT,
    status TEXT,
    erro TEXT,
    executed_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_produtos_nome ON produtos(nome);
CREATE INDEX idx_pedidos_cliente ON pedidos(cliente_id);
CREATE INDEX idx_pedidos_status ON pedidos(status);
