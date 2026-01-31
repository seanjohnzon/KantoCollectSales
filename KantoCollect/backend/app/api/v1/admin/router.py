"""
Admin API router.

All routes in this module require admin authentication.
"""

from fastapi import APIRouter

from .deal_analyzer import router as deal_analyzer_router
from .inventory import router as inventory_router
from .cards import router as cards_router
from .whatnot import router as whatnot_router

router = APIRouter()

# Deal Analyzer endpoints
router.include_router(
    deal_analyzer_router,
    prefix="/deal-analyzer",
    tags=["Deal Analyzer"],
)

# Inventory endpoints
router.include_router(
    inventory_router,
    prefix="/inventory",
    tags=["Inventory"],
)

# Card Database endpoints
router.include_router(
    cards_router,
    prefix="/cards",
    tags=["Card Database"],
)

# WhatNot Sales endpoints
router.include_router(
    whatnot_router,
    prefix="/whatnot",
    tags=["WhatNot Sales"],
)
