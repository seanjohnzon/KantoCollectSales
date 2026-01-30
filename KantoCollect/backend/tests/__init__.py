"""
Test suite for Kanto Collect backend.

This package contains API and UI tests for all KantoCollect tools.

Test Categories:
- API Tests (tests/api/): HTTP endpoint tests using FastAPI TestClient
- UI Tests (tests/ui/): Browser tests using Playwright

Running Tests:
- All tests: pytest
- API only: pytest tests/api/
- UI only: pytest tests/ui/
- Non-admin: pytest -m "not admin"
- Admin only: pytest -m admin
- WhatNot tests: pytest tests/api/admin/test_manage_*.py tests/api/non_admin/test_view_*.py
"""
