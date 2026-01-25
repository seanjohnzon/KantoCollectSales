#!/usr/bin/env python3
"""Test script to verify Excel import with null handling."""
import requests

url = "http://localhost:8000/api/v1/admin/whatnot/import/excel"
headers = {"Authorization": "Bearer 1453"}
excel_file = "/Users/sahcihansahin/Downloads/Jan 2026 - WhatNot Stream Sales .xlsx"

with open(excel_file, 'rb') as f:
    files = {'file': ('test.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
    response = requests.post(url, headers=headers, files=files)

print("Status Code:", response.status_code)
print("\nResponse:")
print(response.json())
