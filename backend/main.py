# backend/main.py
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Carrega variáveis de ambiente
load_dotenv()

# Importa os roteadores dos módulos
from src.fopag.router import router as fopag_router
from src.adiantamento.router import router as adiantamento_router
from src.importacoes_manuais.braga_comissoes.router import router as braga_router

# Inicializa a App
app = FastAPI(
    title="Projecont Auditor Unificado",
    version="4.0.0",
    description="API Unificada: FOPAG (Folha Mensal) + Adiantamento (Legado)",
)

# Configuração CORS (Permite que o Frontend React acesse)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, troque pelo IP do frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- REGISTRO DE ROTAS ---
# 1. Rotas da Folha Mensal (Novo Core)
app.include_router(fopag_router)

# 2. Rotas do Adiantamento (Legado Migrado)
app.include_router(adiantamento_router)

# 3. Importacoes Manuais
app.include_router(braga_router)


@app.get("/")
def health_check():
    """Health Check para garantir que o servidor subiu."""
    return {
        "status": "online",
        "system": "Projecont Auditor Unified",
        "modules": ["fopag", "adiantamento"],
    }


if __name__ == "__main__":
    # Pega porta do .env ou usa 8001 como padrão
    port = int(os.getenv("PORT", 8001))
    print(f"🚀 Servidor subindo na porta {port}...")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
