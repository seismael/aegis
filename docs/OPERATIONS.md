# Aegis V4 Operations

## Reading Governance Health

The `.aegis/telemetry.json` file contains check history:

```json
[
  {"timestamp": "2026-05-23T01:00:00Z", "total_violations": 12, "active_violations": 3, "type": "check"}
]
```

## Enterprise Monitoring

Configure OTLP export in `.aegis/config.yaml`:

```yaml
telemetry:
  exporter: otlp
  otlp_endpoint: "https://otel-collector.example.com/v1/traces"
```

## Server Deployment

For non-stdio environments:

```bash
aegis run --transport sse --host 0.0.0.0 --port 8000
```

## CI/CD Integration

GitHub Actions workflow calls the MCP server to validate:

```yaml
- name: Aegis Governance
  run: |
    aegis run &
    sleep 2
```

No `aegis check` command exists in V4. All governance flows through the MCP server.
