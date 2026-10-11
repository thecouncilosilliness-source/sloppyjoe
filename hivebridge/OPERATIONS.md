# HiveBridge — AI-operated system charter

**Human director:** HiveFather sets mission, strategic priorities, funding boundaries, consent policy, and stop conditions. Routine technical operation is intended to be performed by configured AI agents, not by asking the director to execute commands every day.

**Actual status, October 2026:** The released gateway handles sequential handoffs and local persistence with simulated agent slots. Provider adapters exist but are *not* connected. GitHub Actions can test the source without intervention. The public site requires one-time Pages enablement; a live backend is not running.

## Intended automation boundaries

1. **Routine, read-only work** — Automated readiness checks, health monitoring, logs, retries with backoff, incident drafts, task routing and status summaries.
2. **Drafting and research** — Agents can produce code changes, tests, project plans and proposed operations. They should use pull requests and provenance before publication.
3. **External actions** — Public posting, modifying infrastructure, making purchases, connecting provider accounts, or sharing private material requires capabilities and explicit grants set by the director. No standing blanket permission to spend or post.
4. **Safety and privacy** — Per-provider opt-in, no secret values in Git, restricted data retention, agent identity validation, event audit trails, graceful shutdown, spending caps, human override.
5. **Budget** — Development remains free where possible. An automated action must not incur provider API costs without configured hard limits and funding approval.

## What runs unattended today

The GitHub Actions workflow **HiveBridge unattended readiness checks** runs daily and on relevant pushes. It extracts the released source archive, runs unit tests and an offline Council handoff, verifies the output is labelled simulated, and saves a short readiness record as an Actions artifact. This checks the software; it does **not** create an independent AI operator, provision a service, connect commercial AI APIs, or perform outbound agent actions.

## Next gates for AI-operated deployment

- Verify a reachable static public site and connect the chosen domain using the domain owner's approved DNS settings.
- Deploy the authenticated gateway behind HTTPS with a secure secrets manager, audited operations, cost quotas and protected persistent storage.
- Connect real providers selectively with valid developer API credentials. Consumer chat accounts do not grant unattended API or memory access.
- Add a task queue, approval policy engine, recurring scheduler and restart/health supervision in a controlled runtime.
- Run controlled multi-provider integration tests, including failure and cancellation cases, before claiming autonomous operation.

The director makes strategic decisions. The software must provide meaningful control, auditability, and revocation without requiring the director to babysit routine processes.
