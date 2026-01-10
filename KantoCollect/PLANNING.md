# Kanto Collect - Project Planning

## 🎯 Project Overview

Kanto Collect is an internal toolset for managing a collectibles business, focusing on:
- **Deal Analysis** - AI-powered lot valuation and negotiation assistance
- **Inventory Management** - Track products across sales channels
- **Price Intelligence** - Multi-source pricing data aggregation
- **Future: Online Store** - Customer-facing e-commerce (Lovable design)

---

## 👥 Team & Users

The system is designed for a team of **3 people initially**, with scalability for growth.

| Role | Access Level | Description |
|------|--------------|-------------|
| **Admin** | Full | All tools, user management, settings |
| **Manager** | High | Create events, assign tasks, view reports |
| **Team Member** | Standard | View assigned tasks, update status |

---

## 🏗️ Architecture

### Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI |
| Database | PostgreSQL (prod) / SQLite (dev) |
| ORM | SQLModel (SQLAlchemy + Pydantic) |
| Authentication | JWT + OAuth2, Role-based access |
| AI Vision | Claude API (Anthropic) |
| Price Data | PriceCharting API, eBay API |
| Admin Frontend | React + Tailwind CSS |
| Store Frontend | Lovable (future) |

### Folder Structure

```
KantoCollect/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── core/              # Config, security, database
│   │   ├── models/            # SQLModel database models
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── api/v1/            # API endpoints
│   │   │   ├── admin/         # Admin-only endpoints
│   │   │   │   ├── deal_analyzer.py
│   │   │   │   ├── inventory.py
│   │   │   │   ├── calendar.py    # Calendar & events
│   │   │   │   └── tasks.py       # Task management
│   │   │   └── auth.py        # Authentication
│   │   ├── services/          # Business logic
│   │   │   ├── deal_analyzer/ # Deal analysis service
│   │   │   ├── inventory/     # Inventory service
│   │   │   ├── calendar/      # Calendar service
│   │   │   └── price_lookup/  # Price aggregation
│   │   └── utils/             # Helpers
│   ├── tests/                 # Pytest tests
│   └── alembic/               # Database migrations
├── apps/
│   ├── admin-dashboard/       # Admin UI
│   │   ├── deal-analyzer/     # Deal Analyzer UI
│   │   ├── inventory-tool/    # Inventory UI
│   │   └── calendar-tasks/    # Calendar & Task UI
│   └── store/                 # Online store (future - Shopify)
├── agents/                    # AI agent configurations
├── reference-data/            # Card databases
└── bots/                      # Discord bot (future)
```

---

## 🔐 Authentication & Authorization

### Roles
- **Admin**: Full access to all tools
- **User**: Store access only (future)

### Protected Routes
| Route Pattern | Access |
|---------------|--------|
| `/api/v1/admin/*` | Admin only |
| `/api/v1/store/*` | Public (future) |
| `/api/v1/auth/*` | Public |

---

## 🔌 External Integrations

### PriceCharting (Legendary Subscription)
- **API Key**: Required for price lookups
- **Features Used**: 
  - Price API
  - Deal Alerts
  - Price Lists Download
  - Shopify Integration

### eBay
- **API**: Browse API for sold listings
- **Use Case**: Real transaction verification

### Shopify (Via PriceCharting)
- **Integration**: Through PriceCharting's Shopify linking tool (Legendary feature)
- **Setup Guide**: https://www.pricecharting.com/shopify-integration
- **How it works**:
  1. Create custom Shopify app with Products read/write permissions
  2. Use PriceCharting's linking tool to connect stores
  3. Configure price rules (e.g., "Loose" keyword → "Loose Price")
  4. Set automatic or on-demand price sync
- **Linking Options**: UPC, PriceCharting ID, TCGPlayer ID, Amazon ASIN
- **Categories Supported**: Video Games, Pokemon, Magic, YuGiOh cards

### Whatnot (Pending API Access)
- **Use Case**: Sync live sale inventory

### Claude (Anthropic)
- **Use Case**: AI vision for card detection/identification

---

## 📊 Data Models (Core)

### User
- id, email, password_hash, role, created_at

### Product
- id, name, category, tcg_type, set_code, card_number, variant, language, condition

### Inventory
- id, product_id, quantity, location, cost_basis, listed_price

### DealAnalysis
- id, user_id, images, description, asking_price, total_value, items[], created_at

### PriceHistory
- id, product_id, source, price, recorded_at

---

## 🎨 UI/UX Conventions

- **Color Scheme**: Dark theme with accent colors
- **Typography**: Modern, readable fonts
- **Components**: Consistent button styles, cards, modals
- **Mobile**: Responsive design for on-the-go deal analysis

---

## 📝 Code Conventions

- **Python**: PEP8, Black formatting, type hints
- **Docstrings**: Google style
- **Testing**: Pytest with fixtures
- **API**: RESTful, versioned (`/api/v1/`)
- **Errors**: Consistent error response format

---

## 🚀 Deployment (Future)

- **Backend**: Docker container
- **Database**: Managed PostgreSQL
- **Frontend**: Static hosting (Vercel/Netlify)
- **Domain**: TBD
