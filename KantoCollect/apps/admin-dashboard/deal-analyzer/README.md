# 🔍 Deal Analyzer

AI-powered lot valuation tool for quick deal assessment.

## Features

- 📸 **Image Upload**: Upload photos of card lots
- 🤖 **AI Detection**: Claude Vision identifies cards automatically
- 💰 **Price Lookup**: PriceCharting integration for market values
- 🤝 **Negotiation Help**: Suggested offer prices and profit margins

## Usage Flow

1. Upload image(s) of the card lot
2. Optionally add seller's description
3. Enter asking price (optional)
4. Click "Analyze"
5. Review detected cards and values
6. Use negotiation suggestions

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/admin/deal-analyzer/analyze` | Analyze a deal |
| POST | `/api/v1/admin/deal-analyzer/price-lookup` | Quick price lookup |
| GET | `/api/v1/admin/deal-analyzer/price-lookup/upc/{upc}` | Lookup by barcode |
| GET | `/api/v1/admin/deal-analyzer/search/{query}` | Search products |

## Example Request

```bash
curl -X POST "http://localhost:8000/api/v1/admin/deal-analyzer/analyze" \
  -H "Authorization: Bearer <token>" \
  -F "images=@card_lot.jpg" \
  -F "description=Lot of One Piece cards" \
  -F "asking_price=100" \
  -F "category=one-piece"
```
