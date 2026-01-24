# WhatNot Sales Tracking System

Comprehensive sales tracking and analytics system for WhatNot stream and marketplace sales.

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- FastAPI
- SQLModel
- pandas

### Installation

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Start server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Access

- **UI**: http://localhost:8000/whatnot-sales
- **API Docs**: http://localhost:8000/docs
- **Admin PIN**: 1453

## 📊 Current Data

- **Stream Sales**: 611 transactions across 8 shows (January 2026)
- **Marketplace Orders**: 140 transactions
- **Total Revenue**: $9,677 (streams) + $1,844 (marketplace) = $11,521
- **COGS Coverage**: 51.4% (streams), 0% (marketplace)
- **Database Size**: 592KB (whatnot_sales.db)

## 🎯 Features

### 1. Excel Import
- **Stream Sales**: Auto-detect show name and date from Excel structure
- **Marketplace Orders**: Import from "WhatNot Marketplace" sheet
- Progress indicators with spinner animations
- COGS coverage tracking
- Error handling with detailed feedback

### 2. COGS Mapping System ⭐
- Keyword-based auto-assignment during import
- Priority-ordered rules (higher priority checked first)
- Match types: contains, starts_with, ends_with, exact
- Create rules from Product Catalog UI
- Test rules against sample product names

### 3. Product Catalog
- Static catalog of 26 products with images
- ImageKit CDN integration
- Manual COGS assignment creates auto-mapping rules
- Sales and revenue tracking per product

### 4. Shows Tab (Excel-Style Layout)
- Comprehensive table with all metrics
- Summary stats: Total Shows, Revenue, Earnings, ROI
- Columns: Date, Show Name, Revenue, Commission, Earnings, COGS, Profit, ROI%, Items, Buyers, Avg Order
- Color-coded profit/loss indicators
- Totals footer row

### 5. Marketplace Tab
- Import marketplace orders separately
- Display with payment status
- Track COGS coverage separately from streams

### 6. Analytics
- Dashboard summary
- Top products by revenue/frequency/profit
- Top buyers by spending
- COGS rule performance metrics
- Overall COGS coverage percentage

## 📁 Project Structure

```
KantoCollect/
├── apps/admin-dashboard/whatnot-sales/
│   └── index.html                    # Single-file UI application
├── backend/
│   ├── app/
│   │   ├── api/v1/admin/
│   │   │   ├── whatnot.py            # All API endpoints
│   │   │   └── router.py             # Router configuration
│   │   ├── core/
│   │   │   ├── whatnot_database.py   # Database session management
│   │   │   └── config.py             # Configuration
│   │   ├── models/
│   │   │   └── whatnot.py            # All database models
│   │   └── services/whatnot/
│   │       ├── import_service.py     # Excel import logic
│   │       ├── analytics_service.py  # Analytics queries
│   │       └── cogs_service.py       # COGS matching logic
│   ├── whatnot_sales.db              # SQLite database (592KB)
│   └── PRODUCT_COGS_MAPPING.md       # COGS rules documentation
```

## 🗄️ Database Schema

### Tables

1. **whatnot_shows** - Stream shows
   - Show metadata (date, name, platform)
   - Pre-computed aggregates (revenue, earnings, profit, ROI)
   - Import tracking

2. **sales_transactions** - Individual sales
   - Sale type: 'stream' or 'marketplace'
   - Financial data (gross, discounts, fees, net)
   - COGS and profit calculations
   - Links to products, buyers, inventory

3. **whatnot_products** - Product catalog
   - Normalized product names
   - Aggregated metrics (total sales, revenue, times sold)
   - Optional inventory linking

4. **whatnot_buyers** - Customer data
   - Purchase history and totals
   - First/last purchase dates
   - Repeat buyer tracking

5. **cogs_mapping_rules** ⭐ CRITICAL
   - Rule name and keywords (JSON array)
   - COGS amount (Decimal)
   - Match type and priority
   - Active/inactive toggle
   - Category and notes

### Indexes
- show_id, transaction_date, product_id, buyer_id
- sale_type (stream/marketplace filter)
- master_card_id (inventory linking)

## 🔌 API Endpoints

### Import
- `POST /api/v1/admin/whatnot/import/excel` - Import stream sales
- `POST /api/v1/admin/whatnot/import/marketplace` - Import marketplace orders

### Shows
- `GET /api/v1/admin/whatnot/shows` - List all shows with metrics
- `GET /api/v1/admin/whatnot/shows/{id}` - Show details
- `DELETE /api/v1/admin/whatnot/shows/{id}` - Delete show

### Transactions
- `GET /api/v1/admin/whatnot/transactions` - List with filters
  - `?sale_type=stream` or `?sale_type=marketplace`
  - `?show_id={id}`, `?product_id={id}`, `?buyer_id={id}`
  - `?has_cogs=true/false`

### Products
- `GET /api/v1/admin/whatnot/products` - List all products
- `GET /api/v1/admin/whatnot/product-catalog` - Static catalog
- `POST /api/v1/admin/whatnot/product-catalog/save-cogs` - Save COGS + create rule

### COGS Rules
- `GET /api/v1/admin/whatnot/cogs-rules` - List all rules
- `POST /api/v1/admin/whatnot/cogs-rules` - Create rule
- `PUT /api/v1/admin/whatnot/cogs-rules/{id}` - Update rule
- `DELETE /api/v1/admin/whatnot/cogs-rules/{id}` - Delete rule

### Analytics
- `GET /api/v1/admin/whatnot/analytics/overview` - Dashboard summary
- `GET /api/v1/admin/whatnot/analytics/cogs-rule-performance` - Rule stats

## 🎨 UI Features

### Admin Authentication
- PIN: 1453
- View-only mode by default
- Admin mode unlocks Import, COGS Rules, Product Catalog tabs

### 8 Tabs
1. **Import** - Upload Excel files with progress tracking
2. **Product Catalog** - 26 static products with manual COGS entry
3. **COGS Rules** - Manage keyword-based mapping rules
4. **Shows** - Excel-style table with comprehensive metrics
5. **Marketplace** - Marketplace order display and import
6. **Products** - Product performance analytics
7. **Buyers** - Customer insights and history
8. **Analytics** - Dashboard with overall stats

### Design
- Dark theme (#0f172a background)
- Green accent (#22c55e)
- Responsive layout
- Hover effects and transitions
- Professional table formatting

## 📝 Example COGS Rules

```javascript
// Free Packs and Giveaways
{
  rule_name: "Free Packs - Auto-generated",
  keywords: ["free", "free pack", "free pokemon", "giveaway"],
  cogs_amount: 1.00,
  match_type: "contains",
  priority: 100,
  is_active: true
}

// Booster Bundles
{
  rule_name: "Booster Bundle - Auto-generated",
  keywords: ["booster bundle", "bb"],
  cogs_amount: 15.00,
  match_type: "contains",
  priority: 90
}

// Elite Trainer Boxes
{
  rule_name: "Elite Trainer Box - Auto-generated",
  keywords: ["etb", "elite trainer box"],
  cogs_amount: 40.00,
  match_type: "contains",
  priority: 85
}
```

## 🎯 Goals

- **Primary**: Achieve 80%+ COGS coverage via keyword rules
- Track all WhatNot sales (streams + marketplace)
- Analyze show performance and profitability
- Identify top products and customers
- Optimize pricing and inventory decisions

## 🔄 Workflow

1. **Import Data**
   - Upload Excel files via Import tab
   - System auto-detects show info
   - COGS rules auto-assign costs
   - Review COGS coverage percentage

2. **Assign COGS**
   - Use Product Catalog to set COGS
   - Creates auto-mapping rules
   - Or create manual COGS rules
   - Test rules against existing products

3. **Analyze Performance**
   - Review Shows tab for profitability
   - Check Product performance
   - Identify top buyers
   - Track COGS rule effectiveness

4. **Optimize**
   - Refine COGS rules for better coverage
   - Adjust pricing based on ROI data
   - Focus on high-profit products
   - Nurture repeat buyers

## 📦 Dependencies

```
fastapi>=0.104.0
sqlmodel>=0.0.14
pandas>=2.0.0
python-multipart>=0.0.6
openpyxl>=3.1.0
```

## 🚧 Future Enhancements

- [ ] Multi-platform support (eBay, Shopify)
- [ ] Monthly trend analysis and charts
- [ ] Bulk COGS operations
- [ ] CSV export functionality
- [ ] Auto-import from watched folder
- [ ] Mobile-responsive design
- [ ] Advanced search and filtering
- [ ] Inventory sync (update stock on sale)
- [ ] AI-powered COGS suggestions

## 📊 Sample Data

### Show Example
```json
{
  "id": 5,
  "show_date": "2026-01-09",
  "show_name": "💸🦑💰💸🦑💰 Wheel Spin - Mega Charizard UPCs...",
  "total_gross_sales": "1895.00",
  "total_net_earnings": "1624.69",
  "total_cogs": "96.00",
  "total_net_profit": "1132.22",
  "item_count": 124,
  "unique_buyers": 57,
  "avg_sale_price": "15.28"
}
```

### Transaction Example
```json
{
  "id": 750,
  "show_id": null,
  "sale_type": "marketplace",
  "transaction_date": "2026-01-21",
  "item_name": "Edward.Newgate (Alternate Art)",
  "quantity": 1,
  "buyer_username": "op_pete711",
  "payment_status": "Processing",
  "total_revenue": "36.00",
  "net_earnings": "31.64",
  "cogs": null,
  "net_profit": "31.64"
}
```

## 🔐 Security

- Admin authentication via PIN (1453)
- All endpoints require authentication
- JWT support for future user management
- Database files ignored in .gitignore (forced for backup)

## 📄 License

Proprietary - KantoCollect Internal Use Only

## 🤝 Contributing

This is an internal tool. Contact the development team for access.

## 📞 Support

For questions or issues, contact: sahcihan@kantocollect.com

---

**Last Updated**: January 24, 2026
**Version**: 1.0.0
**Status**: ✅ Production Ready (MVP Complete)
