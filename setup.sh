#!/bin/bash

# Setup script para Echo Transcription API

echo "🚀 Configurando Echo Transcription API..."

# 1. Verificar se Node.js está instalado
if ! command -v node &> /dev/null; then
    echo "❌ Node.js não encontrado. Por favor instale Node.js 18+ primeiro."
    exit 1
fi

# 2. Verificar versão do Node.js
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js 18+ é necessário. Versão atual: $(node -v)"
    exit 1
fi

echo "✅ Node.js $(node -v) encontrado"

# 3. Instalar dependências Python
echo "📦 Instalando dependências Python..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "⚠️  requirements.txt não encontrado"
fi

# 4. Instalar dependências Node.js
echo "📦 Instalando dependências Node.js..."
npm install

# 5. Criar diretórios necessários
echo "📁 Criando diretórios..."
mkdir -p uploads
mkdir -p logs
mkdir -p src/trigger

# 6. Copiar arquivo de configuração
if [ ! -f ".env" ]; then
    echo "📝 Criando arquivo .env..."
    cp .env.example .env
    echo "⚠️  Por favor, configure as variáveis em .env"
fi

# 7. Verificar configuração do Trigger.dev
echo "🔧 Verificando configuração do Trigger.dev..."

if [ -z "$TRIGGER_SECRET_KEY" ]; then
    echo "⚠️  TRIGGER_SECRET_KEY não configurado em .env"
fi

# 8. Executar verificações
echo "🧪 Executando verificações..."

# Verificar se TypeScript compila
echo "   - Verificando TypeScript..."
if npx tsc --noEmit; then
    echo "   ✅ TypeScript OK"
else
    echo "   ❌ Erro no TypeScript"
fi

echo ""
echo "🎉 Setup concluído!"
echo ""
echo "Próximos passos:"
echo "1. Configure as variáveis de ambiente em .env"
echo "2. Configure sua conta no Trigger.dev"
echo "3. Configure sua conta no Modal.com"
echo "4. Execute: npm run dev (para Trigger.dev)"
echo "5. Execute: python app.py (para FastAPI)"
echo ""