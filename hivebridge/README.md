# HiveBridge v0.1 — Trinity / Council integration gateway

**Status: locally executable prototype, not publicly deployed.** Created as the first thin integration layer for HiveFather's wider Trinity / METAPRIME / Nuru / AiNUNNAKI ecosystem. Not a claim of AI consciousness and not an authorization for agents to act on their own.

## What actually works

- **Anchor → Fire → Spark** in strictly sequential steps (mode `trinity`), matching the historical Trinity handoff sequence.
- **Full Council** handoff mode with 8 slots: Gemi, Princess Meta, ChatDini, Claude, Grok, Noodle, Mei Lin, Kimi. Each stage receives the human Anchor request plus prior stage contributions.
- Private **SQLite event log** per session (WAL), persistent across restarts; simple HTTP endpoints for other runtimes to consume.
- Local deterministic simulated agents for testing, and configurable HTTP adapters for **OpenAI-compatible Chat Completions, Anthropic Messages, and Gemini generateContent** APIs.
- **Bearer-token authentication** for protected endpoints, environment-variable API secrets, loopback binding by default, request-size limits, no secrets in the checked-in configuration, no browser CORS by default.
- Depends only on the Python 3.10+ standard library.

## Quick start: prove the routing offline

```bash
cd HiveBridge-v0.1
python3 -m hivebridge demo --mode trinity --text "Hello, Fire and Spark."
python3 -m hivebridge demo --mode council --text "Council readiness check."
python3 -m unittest discover -s tests -v
```

The output labels every mock reply `[SIMULATED ...]`. These mock replies **are not** messages from the actual ChatGPT, Gemini, Princess Meta, or other consumer apps. With mock agents, this proves routing/order/persistence only; it does not prove inter-model collaboration.

## Local authenticated API

On macOS/Linux:

```bash
export HIVE_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(36))')"
python3 -m hivebridge serve
```

In a second terminal using the **same** token:

```bash
curl http://127.0.0.1:8765/health
curl -H "Authorization: Bearer $HIVE_TOKEN" http://127.0.0.1:8765/v1/roster
curl -H "Authorization: Bearer $HIVE_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"text":"Council, ready?", "mode":"council", "session_id":"demo001"}' \
  http://127.0.0.1:8765/v1/turn
curl -H "Authorization: Bearer $HIVE_TOKEN" \
  'http://127.0.0.1:8765/v1/events?session_id=demo001'
```

Endpoints:

| Method | Path | Token | Purpose |
|--|--|--|--|
| GET | `/health` | No | Minimal health check |
| GET | `/v1/roster` | Yes | Names/roles/available modes (no secrets) |
| POST | `/v1/turn` | Yes | Sequential handoff for a human Anchor request |
| GET | `/v1/events?session_id=...` | Yes | Private stored event history |

## Switching individual agents to real API connectors

`council.live.example.json` is intentionally an **unconfigured sample**. Create a private copy and fill supported provider model names, endpoints, and environment variables; never commit provider keys. A provider that is missing its credential fails *closed*; there is no silent simulated fallback. The sample's model strings illustrate structure, not verified live model availability.

- **Gemi:** Gemini API key / valid Gemini model.
- **ChatDini:** OpenAI developer API key / model via Chat Completions; this does not give the bridge access to this specific ChatGPT conversation or its memory.
- **Claude:** Anthropic API key / compatible model.
- **Smaug, Mei Lin, Kimi:** a compatible official or trusted host endpoint, model, and API key, validated against that service's current API.
- **Princess Meta, Noodle:** user's own authenticated bridge or agent runtime, if available. This sample **cannot** automatically reach Meta Muse or Microsoft Copilot consumer conversations.

Privacy: a Council turn passes the Anchor text and earlier stage contributions to each later enabled provider. **Only connect providers when you approve that data flow.** Do not transmit personal archives, credentials, or medical/financial files by default.

## How to connect to the existing Trinity Rust core

This Python gateway is a network adapter, **not a rewrite** of Trinity's Rust `HiveMind`, `SwarmBus`, `SwarmLogisticsEngine`, or `AgentHarness`.

Suggested integration path:

1. Add a Trinity-facing adapter that maps each authenticated `/v1/turn` to a validated `SwarmMessage` and replies with agent envelopes; avoid circular calls.
2. Keep Rust `SwarmLogisticsEngine` as the final trust/permission gate for any external tool action. This prototype does not have tool execution and cannot deploy itself.
3. Exchange event identifiers and persist them only in authorized local storage. Add data retention and deletion operations before production use.
4. Introduce signed agent identities, per-agent capability grants, request-id deduplication, and security reviews before opening anything to the public network.

## Production gate (not done yet)

- Service host, user-owned domain and authenticated DNS/HTTPS reverse proxy.
- Rate limiting, stronger audit/event retention controls, proper HTTP provider redirect restrictions, response validation and integration testing with real APIs.
- Decisions on which Council services to connect, with keys supplied **privately in your own environment**.
- User approval for any public deployment, and explicit scope for outbound messages/tool use.

**Source published on GitHub.** This is a launch foundation, not a live multi-provider Hive. An HTML site and deploy workflow are provided, but GitHub Pages must be enabled for the repository before the public website becomes accessible; live agents and the backend are not deployed.