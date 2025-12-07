# Multi-Agent Enterprise System

A hierarchical multi-agent system for enterprise operations built with LangGraph, integrated with Odoo ERP and accessible via Telegram and REST API.

## Architecture Overview

```
+------------------------------------------------------------------+
|                      CLIENT LAYER                                 |
|  Telegram Bot  |  Web Dashboard  |  REST API                     |
+------------------------------------------------------------------+
                               |
+------------------------------------------------------------------+
|                      API GATEWAY (FastAPI)                        |
+------------------------------------------------------------------+
                               |
+------------------------------------------------------------------+
|                  AGENT ORCHESTRATION LAYER                        |
|  +-----------------------------------------------------------+   |
|  |               EXECUTIVE AGENT (Supervisor)                 |   |
|  +---------------------------+-------------------------------+   |
|                              |                                    |
|           +------------------+------------------+                 |
|           v                                     v                 |
|  +---------------------+           +------------------------+    |
|  |  CONTRACTS AGENT    |           |     HR AGENT           |    |
|  +---------------------+           +------------------------+    |
+------------------------------------------------------------------+
                               |
+------------------------------------------------------------------+
|                  DATA & PERSISTENCE LAYER                         |
|  PostgreSQL  |  Redis  |  Odoo ERP                               |
+------------------------------------------------------------------+
```

## Features

### Executive Agent (Orchestrator)
- Task classification and routing
- Sub-agent coordination
- State management
- Response aggregation

### Contracts Agent
- Contract lifecycle management
- Deadline tracking and alerts
- Expiration monitoring
- ERP integration for contracts

### HR Agent
- Employee information management
- Leave requests and approvals
- Recruitment pipeline
- Attendance tracking
- Department organization

## Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose (optional)
- Odoo ERP instance with API access
- Google AI API key
- Telegram Bot Token (optional)

### Installation

1. **Clone and setup:**
```bash
cd Odoo-Work
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your credentials
```

3. **Run the application:**
```bash
uvicorn src.main:app --reload --port 8000
```

### Using Docker

```bash
cd docker
docker-compose up -d
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ODOO_URL` | Odoo server URL | Yes |
| `ODOO_DB` | Odoo database name | Yes |
| `ODOO_USERNAME` | Odoo username | Yes |
| `ODOO_PASSWORD` | Odoo API key/password | Yes |
| `GOOGLE_API_KEY` | Google Gemini API key | Yes |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | No |
| `WEBHOOK_URL` | Public URL for webhooks | No |
| `DATABASE_URL` | PostgreSQL connection URL | No |
| `REDIS_URL` | Redis connection URL | No |

## API Endpoints

### Chat
- `POST /api/v1/chat` - Send message to agent system
- `GET /api/v1/agents/status` - Get agent status

### Contracts
- `GET /api/v1/contracts` - List contracts
- `GET /api/v1/contracts/{id}` - Get contract details
- `POST /api/v1/contracts` - Create contract
- `PUT /api/v1/contracts/{id}` - Update contract
- `GET /api/v1/contracts/expiring` - Get expiring contracts

### HR
- `GET /api/v1/employees` - List employees
- `GET /api/v1/employees/{id}` - Get employee details
- `GET /api/v1/leaves` - List leave requests
- `POST /api/v1/leaves` - Create leave request
- `POST /api/v1/leaves/{id}/approve` - Approve leave

### Health
- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed component status

## Telegram Bot Commands

- `/start` - Welcome message
- `/help` - Show help
- `/contracts` - Contract management menu
- `/hr` - HR operations menu
- `/status` - System status
- `/new` - Start new conversation

## Project Structure

```
Odoo-Work/
+-- src/
|   +-- agents/           # Agent implementations
|   |   +-- executive/    # Main orchestrator
|   |   +-- contracts/    # Contract agent
|   |   +-- hr/           # HR agent
|   |   +-- supervisor.py # LangGraph supervisor
|   +-- api/              # FastAPI routes
|   +-- integrations/     # External integrations
|   |   +-- odoo/         # Odoo XML-RPC client
|   |   +-- telegram/     # Telegram bot
|   |   +-- google/       # Gemini LLM
|   +-- core/             # Core utilities
|   +-- config.py         # Configuration
|   +-- main.py           # Entry point
+-- docker/               # Docker configuration
+-- tests/                # Test suite
+-- requirements.txt
+-- .env
```

## Adding New Agents

1. Create agent module in `src/agents/new_agent/`
2. Define prompts in `prompts.py`
3. Implement tools in `tools.py`
4. Register in `src/agents/supervisor.py`
5. Update Executive Agent prompt with routing rules

## Development

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black src/
isort src/
```

## License

Proprietary - Ailigent AI

## Support

For issues and feature requests, contact the development team.
