# 🛠️ Kanto Collect Admin Dashboard

Internal admin tools for managing the collectibles business.

## Tools

### 1. Deal Analyzer (`/deal-analyzer`)
AI-powered lot valuation and negotiation assistant.
- Upload card lot images
- Get instant valuations
- Negotiation suggestions

### 2. Inventory Tool (`/inventory`) - Coming Soon
Inventory management across all sales channels.
- Product management
- Stock tracking
- Barcode scanning
- Whatnot sync

## Tech Stack

- React 18+
- Tailwind CSS
- React Query
- React Router

## Development

```bash
cd apps/admin-dashboard
npm install
npm run dev
```

## API Integration

All admin endpoints require authentication:
```
Authorization: Bearer <token>
```

Base URL: `http://localhost:8000/api/v1/admin/`
