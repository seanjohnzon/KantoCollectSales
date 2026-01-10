# 📚 Reference Data

Local reference databases for card identification and validation.

## Purpose

These files help the AI and price lookup services:
- Validate card identifications
- Map set codes to full names
- Identify variants and special editions
- Cross-reference product IDs

## Files

### One Piece TCG
- `one-piece/sets.json` - All OP sets with release dates
- `one-piece/variants.json` - Known variant types (SP, Alt-Art, etc.)

### Pokémon TCG  
- `pokemon/sets.json` - Modern and vintage set list
- `pokemon/sealed_products.json` - Known sealed product SKUs

## Usage

The Deal Analyzer service loads these files to:
1. Validate AI card detections
2. Correct common misidentifications
3. Map short names to full product names

## Updating

When new sets release:
1. Add to appropriate sets.json
2. Add any new variant types
3. Restart the backend service

## Format

```json
{
  "sets": [
    {
      "code": "OP-01",
      "name": "Romance Dawn",
      "release_date": "2022-07-22",
      "card_count": 121
    }
  ]
}
```
