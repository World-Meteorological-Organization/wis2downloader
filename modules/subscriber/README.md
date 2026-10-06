# Subscriber Module

MQTT client for connecting to WIS2 Global Brokers and receiving notifications.

## Overview

This module provides:
- MQTT client with TLS/WebSocket support
- Valkey PubSub listener for subscription commands
- Automatic reconnection on connection failures
- Integration with Celery for task dispatch

## Documentation

- [Developer Guide](../../docs/developer-guide.adoc) - Architecture and code details
- [Admin Guide](../../docs/admin-guide.adoc) - Configuration

## Entry Points

- `subscriber_start` - CLI entry point for starting the subscriber service

## Key Files

| File | Description |
|------|-------------|
| `manager.py` | Entry point, thread management |
| `subscriber.py` | MQTT client wrapper |
| `command_listener.py` | Valkey PubSub listener for commands |

## Architecture

```
┌─────────────────┐     Valkey PubSub      ┌──────────────────┐
│  Subscription   │ ──────────────────────▶│ CommandListener  │
│    Manager      │    (commands)         │    (Thread)      │
└─────────────────┘                       └────────┬─────────┘
                                                   │
                                                   ▼
┌─────────────────┐                       ┌──────────────────┐
│  WIS2 Global    │ ◀────────────────────│    Subscriber    │
│     Broker      │       MQTT            │   (MQTT Client)  │
└────────┬────────┘                       └────────┬─────────┘
         │                                         │
         │ Notifications                           │ Celery Tasks
         ▼                                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      Celery Workers                          │
└─────────────────────────────────────────────────────────────┘
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GLOBAL_BROKER_HOST` | - | WIS2 Global Broker hostname (required) |
| `GLOBAL_BROKER_PORT` | `443` | Broker port |
| `GLOBAL_BROKER_USERNAME` | `everyone` | MQTT username |
| `GLOBAL_BROKER_PASSWORD` | `everyone` | MQTT password |
| `MQTT_PROTOCOL` | `websockets` | Transport: `websockets` or `tcp` |
| `MQTT_SESSION_ID` | auto-generated | Persistent session ID |
