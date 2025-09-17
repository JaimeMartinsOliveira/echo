
# Echo - API de Transcrição de Áudio/Vídeo

Echo é uma API robusta e escalável para transcrição de áudio e vídeo, utilizando WhisperX para alta precisão. Sua arquitetura combina FastAPI com serviços modernos como Trigger.dev para orquestração e Modal para computação em GPU, garantindo processamento assíncrono eficiente de arquivos longos.

## ✨ Funcionalidades

- Transcrição de Alta Precisão: Modelo large-v2 do WhisperX para resultados confiáveis.
- Upload Flexível: Aceita uploads diretos de arquivos ou URLs públicos.
- Processamento Assíncrono: Jobs longos são gerenciados em background.
- Notificações via Webhook: Receba atualizações sobre progresso e conclusão.
- Consulta de Status: Endpoints para acompanhar qualquer job.
- Resultados em Múltiplos Formatos: txt, json, srt ou vtt.
- Escalabilidade: Arquitetura pronta para escalar horizontalmente com Docker, Modal e Trigger.dev.
- Cache de Resultados: Redis para acelerar consultas repetidas.

## 🏗️ Arquitetura
```bash
  Cliente → FastAPI → Trigger.dev → Modal (GPU)  
  ↓                     ↓  
  Base de Dados          Webhook  
  ↓                     ↓  
  Redis (Cache) ← Atualiza Status
```


Fluxo detalhado:

1. Recebe pedido via /upload/file ou /upload/url.
2. Cria job no banco de dados (pending).
3. Trigger.dev orquestra execução do job.
4. Modal executa processamento com GPU usando WhisperX.
5. Worker processa o áudio/vídeo.
6. Resultado é enviado ao webhook da API.
7. Status do job é atualizado e resultado armazenado no Redis.

## 🛠️ Tecnologias Utilizadas

- Backend: FastAPI, Python 3.11
- Transcrição: WhisperX, Pyannote.audio, Faster-Whisper
- Orquestração: Trigger.dev
- Computação GPU: Modal
- Base de Dados: SQLite (substituível por PostgreSQL)
- Cache: Redis
- Containerização: Docker, Docker Compose
- Validação: Pydantic
- Dependências principais: fastapi, uvicorn, sqlalchemy, httpx, whisperx, @trigger.dev/sdk

## 🚀 Começando

### Pré-requisitos

- Docker e Docker Compose
- Node.js e npm (para Trigger.dev local)
- Conta na Trigger.dev e Modal

### 1. Clonar o repositório

```bash
git clone <URL_DO_REPOSITORIO>
cd <NOME_DO_REPOSITORIO>
```

### 2. Configurar ambiente

Copie o arquivo de exemplo .env.example:

```bash
cp .env.example .env
```

Preencha as variáveis de ambiente:

| Variável | Descrição |
|----------|-----------|
| PORT | Porta da API (default: 8000) |
| APP_URL | URL pública da API (para webhooks) |
| MODAL_TOKEN_ID | Token ID da Modal |
| MODAL_TOKEN_SECRET | Token Secret da Modal |
| MODAL_WEBHOOK_URL | URL do endpoint FastAPI para receber jobs da Modal |
| TRIGGER_SECRET_KEY | Chave secreta Trigger.dev |
| TRIGGER_PROJECT_ID | ID do projeto Trigger.dev |
| UPLOAD_DIR | Diretório para arquivos (default: ./uploads) |
| MAX_FILE_SIZE | Tamanho máximo do arquivo (default: 500MB) |
| DATABASE_URL | URL de conexão com DB (default: sqlite:///./transcriptions.db) |
| REDIS_URL | URL do Redis (default: redis://redis:6379) |
| JWT_SECRET | (Opcional) Chave para JWT |

### 3. Executar a aplicação

```bash
docker-compose up --build
```

A API estará disponível em http://localhost:8000.

## 📖 Endpoints da API

**Prefixo:** /api/v1

**Upload** 

- `POST /upload/file` – Upload de arquivo  
- `POST /upload/url` – Transcrição via URL

**Transcrição**

- `GET /transcription/{job_id}` – Status e resultado  
- `GET /transcription/{job_id}/download` – Download em txt, json, srt ou vtt  
- `DELETE /transcription/{job_id}` – Cancelar job  
- `GET /transcriptions` – Listar jobs com paginação

**Webhooks**

- `POST /webhooks/transcription` – Receber updates do worker Modal/Trigger.dev

## 📁 Estrutura do Projeto

```
.
├── src
│   ├── api
│   │   ├── routes          # Endpoints (upload, transcription, webhooks)
│   │   └── middleware      # Middlewares (ex: auth)
│   ├── database
│   │   ├── models.py       # Modelos SQLAlchemy
│   │   └── connection.py   # Conexão DB
│   ├── models              # Modelos Pydantic
│   ├── services            # Lógica de negócio
│   ├── utils               # Funções utilitárias
│   ├── trigger             # Tarefas Trigger.dev (TypeScript)
│   └── modal_functions     # Workers WhisperX (GPU)
├── app.py                  # Entrada FastAPI
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── package.json            # Dependências Node.js Trigger.dev
└── trigger.config.ts       # Config Trigger.dev
```

## 🤝 Contribuições

Contribuições são bem-vindas! Abra uma issue ou envie um pull request.

## 📄 Licença

MIT License – veja o arquivo LICENSE para detalhes.
