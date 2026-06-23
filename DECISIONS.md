# AISHA AI - Architectural Decisions

## Overview
This file documents major architectural decisions and their rationale.

## Authentication
See: [backend/app/auth/DECISIONS.md](./backend/app/auth/DECISIONS.md)

### Quick Summary
- Password hashing: bcrypt (cost 12)
- Token type: JWT (30 min expiration)
- Unique identifier: Phone number (African context)

## Database
See: [backend/app/database/DECISIONS.md](./backend/app/database/DECISIONS.md) (Coming soon)

## API Framework
- FastAPI (async, modern, good for AI integration)

## Frontend
- React + Vite (fast, modern)