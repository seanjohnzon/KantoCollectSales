# 📦 Inventory Tool

Central inventory management for all sales channels.

## Status: Planned (Phase 3)

## Planned Features

### Core Inventory
- Product CRUD operations
- Stock level tracking
- Category management
- Condition grading

### Scanning
- Barcode/UPC scanning
- Quick product lookup
- Fast add to inventory

### Integrations
- Whatnot sync (when API available)
- Shopify sync via PriceCharting
- Export to CSV/Excel

### Alerts
- Low stock notifications
- Price change alerts
- Restock reminders

## API Endpoints (Coming Soon)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/inventory/` | List all inventory |
| POST | `/api/v1/admin/inventory/` | Add product |
| GET | `/api/v1/admin/inventory/{id}` | Get product |
| PUT | `/api/v1/admin/inventory/{id}` | Update product |
| DELETE | `/api/v1/admin/inventory/{id}` | Delete product |

---

*Development will begin after Deal Analyzer is complete.*
