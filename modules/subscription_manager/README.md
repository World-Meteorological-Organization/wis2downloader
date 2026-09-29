# Subscription Manager Module

Flask REST API for managing WIS2 data subscriptions.

## Overview

This module provides:
- REST API for creating, listing, and deleting subscriptions
- Prometheus metrics endpoint
- Swagger UI for API documentation
- Valkey PubSub integration for communicating with the subscriber service

## Documentation

- [API Reference](../../docs/api-reference.adoc) - Complete REST API documentation
- [Developer Guide](../../docs/developer-guide.adoc) - Architecture and code details
- [OpenAPI Spec](subscription_manager/static/openapi.yml) - Machine-readable API specification

## Entry Points

- `subscription_manager.app:app` - Flask application (WSGI)
- `subscription_manager.app:run` - Development server

## Key Files

| File | Description |
|------|-------------|
| `app.py` | Flask application with all endpoints |
| `static/openapi.yml` | OpenAPI 3.0 specification |
| `templates/swagger.html` | Swagger UI template |
