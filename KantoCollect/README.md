# 🎴 Kanto Collect

Internal tools for managing a collectibles business - inventory tracking, deal analysis, and price intelligence.

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL (or SQLite for local dev)
- Node.js 18+ (for admin dashboard)

### Setup

1. **Clone and enter the project**
   ```bash
   cd KantoCollect
   ```

2. **Set up Python environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Initialize database**
   ```bash
   cd backend
   alembic upgrade head
   ```

5. **Run the backend**
   ```bash
   uvicorn app.main:app --reload
   ```

6. **Access the API docs**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

---

## 🔑 Required API Keys

| Service | Where to Get | Required For |
|---------|--------------|--------------|
| PriceCharting | [pricecharting.com/api](https://www.pricecharting.com/api-documentation) | Price lookups |
| Anthropic (Claude) | [console.anthropic.com](https://console.anthropic.com/) | AI card detection |
| eBay | [developer.ebay.com](https://developer.ebay.com/) | Sold listings |
| Shopify | Your Shopify Admin | Store integration |

---

## 🛠️ Tools

### Deal Analyzer
AI-powered lot valuation tool. Upload photos of card lots, get instant valuations and negotiation suggestions.

**Features:**
- 📸 Image-based card detection
- 🔍 Automatic card identification
- 💰 Multi-source price lookup
- 🤝 Negotiation recommendations

### Inventory Tool
Track all your inventory across sales channels.

**Features:**
- 📦 Product management
- 📱 Barcode scanning
- 📊 Stock alerts
- 🔗 Whatnot sync (coming soon)

---

## 📁 Project Structure

```
KantoCollect/
├── backend/           # FastAPI backend
├── apps/
│   ├── admin-dashboard/   # Admin tools UI
│   └── store/             # Customer store (future)
├── agents/            # AI agent configs
├── reference-data/    # Card databases
└── bots/              # Discord bot (future)
```

---

## 📝 Documentation

- [PLANNING.md](./PLANNING.md) - Architecture and design decisions
- [TASK.md](./TASK.md) - Current tasks and progress

---

## 🤝 Development

See [PLANNING.md](./PLANNING.md) for coding conventions and architecture details.
