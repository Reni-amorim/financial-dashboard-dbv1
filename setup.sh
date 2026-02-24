#!/bin/bash

# Script de inicialização do Financial Dashboard
# Execute: chmod +x setup.sh && ./setup.sh

set -e

echo "🚀 Iniciando setup do Financial Dashboard..."
echo ""

# Cores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Verifica se Docker está instalado
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker não encontrado. Por favor, instale o Docker primeiro.${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose não encontrado. Por favor, instale o Docker Compose primeiro.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker e Docker Compose encontrados${NC}"
echo ""

# Cria arquivo .env se não existir
if [ ! -f .env ]; then
    echo -e "${BLUE}📝 Criando arquivo .env...${NC}"
    cp .env.example .env
    
    # Gera SECRET_KEY aleatória
    SECRET_KEY=$(openssl rand -hex 32)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/your-super-secret-key-change-in-production-use-openssl-rand-hex-32/$SECRET_KEY/g" .env
    else
        # Linux
        sed -i "s/your-super-secret-key-change-in-production-use-openssl-rand-hex-32/$SECRET_KEY/g" .env
    fi
    
    echo -e "${GREEN}✅ Arquivo .env criado com SECRET_KEY gerada${NC}"
else
    echo -e "${BLUE}📝 Arquivo .env já existe${NC}"
fi
echo ""

# Cria diretórios necessários
echo -e "${BLUE}📁 Criando diretórios...${NC}"
mkdir -p data/raw data/processed
echo -e "${GREEN}✅ Diretórios criados${NC}"
echo ""

# Gera arquivo XLSX de exemplo


# Escolha de execução
echo -e "${BLUE}Como você quer executar?${NC}"
echo "1) Docker (Recomendado - mais fácil)"
echo "2) Desenvolvimento local (requer Python 3.11+)"
read -p "Escolha (1 ou 2): " choice

if [ "$choice" == "1" ]; then
    echo ""
    echo -e "${BLUE}🐳 Iniciando com Docker...${NC}"
    echo ""
    
    # Para containers antigos se existirem
    docker-compose down 2>/dev/null || true
    
    # Builda e sobe containers
    echo -e "${BLUE}🔨 Building containers...${NC}"
    docker-compose build
    
    echo ""
    echo -e "${BLUE}🚀 Iniciando containers...${NC}"
    docker-compose up -d
    
    echo ""
    echo -e "${GREEN}✅ Setup completo!${NC}"
    echo ""
    echo -e "${BLUE}📍 Acessos:${NC}"
    echo "  🌐 Frontend (Streamlit): http://localhost:8501"
    echo "  🔌 Backend (FastAPI):    http://localhost:8000"
    echo "  📚 Docs API:             http://localhost:8000/docs"
    echo "  🗄️  PostgreSQL:           localhost:5432"
    echo ""
    echo -e "${BLUE}📋 Comandos úteis:${NC}"
    echo "  docker-compose logs -f          # Ver logs"
    echo "  docker-compose down             # Parar containers"
    echo "  docker-compose up -d            # Iniciar containers"
    echo "  docker-compose restart backend  # Reiniciar backend"
    echo ""
    
elif [ "$choice" == "2" ]; then
    echo ""
    echo -e "${BLUE}💻 Setup para desenvolvimento local...${NC}"
    echo ""
    
    # Verifica Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python3 não encontrado. Instale Python 3.11+${NC}"
        exit 1
    fi
    
    # PostgreSQL
    echo -e "${BLUE}🗄️  Iniciando PostgreSQL com Docker...${NC}"
    docker run -d \
        --name financial_postgres \
        -e POSTGRES_USER=postgres \
        -e POSTGRES_PASSWORD=postgres \
        -e POSTGRES_DB=financial_db \
        -p 5432:5432 \
        postgres:16-alpine
    
    echo -e "${GREEN}✅ PostgreSQL rodando${NC}"
    echo ""
    
    # Backend
    echo -e "${BLUE}🔧 Configurando backend...${NC}"
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    
    echo ""
    echo -e "${BLUE}📊 Criando tabelas no banco...${NC}"
    python -c "from app.database import init_db; init_db()"
    echo -e "${GREEN}✅ Backend configurado${NC}"
    cd ..
    echo ""
    
    # Frontend
    echo -e "${BLUE}🎨 Configurando frontend...${NC}"
    cd frontend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    echo -e "${GREEN}✅ Frontend configurado${NC}"
    cd ..
    echo ""
    
    echo -e "${GREEN}✅ Setup completo!${NC}"
    echo ""
    echo -e "${BLUE}Para iniciar o sistema:${NC}"
    echo ""
    echo "Terminal 1 (Backend):"
    echo "  cd backend"
    echo "  source venv/bin/activate"
    echo "  uvicorn app.main:app --reload"
    echo ""
    echo "Terminal 2 (Frontend):"
    echo "  cd frontend"
    echo "  source venv/bin/activate"
    echo "  streamlit run app.py"
    echo ""
    echo -e "${BLUE}📍 Acessos:${NC}"
    echo "  🌐 Frontend: http://localhost:8501"
    echo "  🔌 Backend:  http://localhost:8000"
    echo "  📚 Docs:     http://localhost:8000/docs"
    echo ""
else
    echo -e "${RED}Opção inválida${NC}"
    exit 1
fi

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 Tudo pronto! Bom desenvolvimento!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
