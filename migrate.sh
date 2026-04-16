#!/bin/bash
# DB migration bootstrap for restaurant-service.
# Migration 001 is a no-op baseline — safe to run from scratch.
set -e

echo "=== DB Migration: restaurant-service ==="
echo "Running: alembic upgrade head"
alembic upgrade head
echo "=== Migration complete ==="
