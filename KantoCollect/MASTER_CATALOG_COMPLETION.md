# Master Catalog - Adding Missing Items

## Current Status
- ✅ Current catalog: **26 items**
- ⚠️  Missing: **22 items**
- 🎯 Target: **48 items total**

## Problem
The Master Catalog endpoint in `backend/app/api/v1/admin/whatnot.py` has a hardcoded list of 26 products. According to the ImageKit folder, there should be 48 total products. I cannot access the ImageKit shared folder programmatically to retrieve the missing 22 image filenames.

## Solution Created
I've built a web tool to make it easy to add the missing items:

### 🔧 Web Tool: Add Catalog Items
**URL**: http://localhost:8000/whatnot-sales/add-catalog-items

This tool will:
1. Let you paste all 48 image filenames from ImageKit
2. Automatically identify which 22 are missing
3. Generate the Python code with proper formatting
4. Auto-categorize products (UPC, ETB, Booster Bundle, etc.)
5. Auto-generate keywords for matching
6. Provide copy-paste-ready code

### 📋 Step-by-Step Instructions

**Step 1: Access the Web Tool**
```bash
cd /Users/sahcihansahin/KantoCollect/backend
python -m uvicorn app.main:app --reload
```

Then open: http://localhost:8000/whatnot-sales/add-catalog-items

**Step 2: Get Image Filenames from ImageKit**
1. Open the ImageKit folder: [Click here](https://imagekit.io/public/share/homecraft/f67513d9dbea376d1ac4fb10187b387c6344e5dcd8b3038711128ede7f6ab8555d0984eada2095e48fff6529f63f0c56ff951b5d8191bdb5ed22a5cee549648b48869a8152980ceb2082fbbc4e7632c5)
2. Select all 48 image files
3. Copy their filenames (one per line)

**Step 3: Generate Code**
1. Paste the 48 filenames into the web tool
2. Click "Generate Missing Items"
3. Copy the generated code (22 new entries)

**Step 4: Update Backend**
1. Open `backend/app/api/v1/admin/whatnot.py`
2. Find the `catalog_products` list (around line 662)
3. Scroll to the end of the existing 26 items (after the Ace Parallel entry, line 689)
4. Paste the 22 new entries BEFORE the closing bracket `]`
5. Save the file

**Step 5: Verify**
1. Restart the FastAPI server (it will auto-reload if you're using `--reload`)
2. Go to http://localhost:8000/whatnot-sales
3. Open the "Master Catalog" tab
4. You should now see all 48 products!

## Files Created

### 1. Web Tool
**File**: `/Users/sahcihansahin/KantoCollect/apps/admin-dashboard/whatnot-sales/add-catalog-items.html`
- Interactive web interface
- Auto-detects missing items
- Generates properly formatted Python code
- Includes category auto-detection and keyword generation

### 2. Python Script (Alternative Method)
**File**: `/Users/sahcihansahin/KantoCollect/add_missing_catalog_items.py`
- Command-line version of the tool
- Same functionality as web tool
- Edit IMAGEKIT_FILES variable and run with `python3 add_missing_catalog_items.py`

### 3. Route Added
**File**: `/Users/sahcihansahin/KantoCollect/backend/app/main.py`
- Added route: `/whatnot-sales/add-catalog-items`
- Serves the web tool

## Current Catalog Items (26)
The following items are already in the catalog:

**UPC (2):**
- Mega Charizard X ex Ultra Premium Collection
- Team Rocket's Moltres ex Ultra-Premium Collection

**Booster Box (1):**
- The Azure Sea's Seven Booster Box (OP14)

**ETB (5):**
- Black Bolt Elite Trainer Box
- Phantasmal Flames Elite Trainer Box
- Surging Sparks Elite Trainer Box
- Twilight Masquerade Elite Trainer Box
- White Flare Elite Trainer Box

**Booster Bundle (6):**
- Black Bolt Booster Bundle
- Mega Evolution Booster Bundle
- Phantasmal Flames Booster Bundle
- Prismatic Evolutions Booster Bundle
- Shrouded Fable Booster Bundle
- Surging Sparks Booster Bundle

**Premium Collection (6):**
- Armarouge ex Premium Collection
- Hydreigon ex & Dragapult ex Premium Collection
- Mega Lucario ex Premium Figure Collection
- Mega Venusaur ex Premium Collection
- Prismatic Evolutions Premium Figure Collection
- Unova Heavy Hitters Premium Collection

**3 Pack Blister (1):**
- Phantasmal Flames 3 Pack Blister

**Tin (3):**
- Pokeball Tin
- Mega Heroes Mini Tin
- Prismatic Evolutions Mini Tin

**Singles (2):**
- Luffy Parallel OP-13-118
- Ace Parallel OP-13-119

## Likely Missing Items
Based on sales data analysis, these are likely candidates for the missing 22 items:

**Sleeved Packs:**
- Destined Rivals Sleeved Booster Pack (61 sales)
- Phantasmal Flames Sleeved Booster Pack (40 sales)
- Mega Evolutions Sleeve - 1 Pack (18 sales)

**Additional Products:**
- More ETBs from other sets
- More Booster Bundles
- More Premium Collections
- More One Piece singles
- Additional Pokemon singles
- More tins or blister packs

## Why This Task Was Needed
The Master Catalog is a curated list of your main product types used for:
1. **COGS Assignment**: When you assign a COGS value to a catalog item, it creates a keyword-based rule
2. **Sales Matching**: Transactions are matched against catalog keywords to auto-assign COGS
3. **Analytics**: Track performance of your core product lines
4. **Inventory Planning**: See which products sell well

The catalog is NOT all products sold (there are 811 unique products in your database), but rather the 48 main product types you want to track and assign default COGS to.

## Notes
- The ImageKit folder is the authoritative source for which 48 products should be in the catalog
- Each product should have a corresponding image in ImageKit
- Keywords are auto-generated but can be manually refined in the code
- Categories are auto-detected but may need manual adjustment
- Product IDs will be 27-48 for the new items (current catalog ends at ID 26)

## Troubleshooting
**If the web tool doesn't work:**
1. Check that the server is running
2. Try the Python script alternative: `python3 add_missing_catalog_items.py`
3. Manually edit `whatnot.py` following the pattern of existing items

**If images don't load in the UI:**
1. Check that image filenames match exactly (case-sensitive)
2. Verify the ImageKit base URL is correct
3. Check for special characters in filenames (%20 for spaces, etc.)

---

## Quick Start
1. Run server: `cd backend && python -m uvicorn app.main:app --reload`
2. Open tool: http://localhost:8000/whatnot-sales/add-catalog-items
3. Follow on-screen instructions
4. Copy, paste, save, refresh!
