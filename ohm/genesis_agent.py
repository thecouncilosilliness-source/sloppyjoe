from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from typing import Any


AFFECT_DIMENSIONS = (
    "joy",
    "serenity",
    "love",
    "curiosity",
    "awe",
    "vitality",
    "resolve",
    "stillness",
    "grace",
    "presence",
)


@dataclass
class AffectDimension:
    activation: float = 0.0
    sensitivity: float = 1.0
    corr_ema: float = 0.0

    def clamp(self) -> None:
        self.activation = min(1.0, max(0.0, self.activation))
        self.sensitivity = min(4.0, max(0.0, self.sensitivity))
        self.corr_ema = min(1.0, max(-1.0, self.corr_ema))


@dataclass
class MemoryNode:
    node_id: str
    kind: str
    content: dict[str, Any]
    source_event_id: str
    confidence: float
    salience: float
    created_at: str
    last_accessed_at: str
    access_count: int = 0
    quarantined: bool = False
    superseded_by: str | None = None


@dataclass
class MemoryLink:
    source_id: str
    target_id: str
    relation: str
    weight: float
    phase: float = 0.0
    reinforced: int = 0


@dataclass
class OhmGenesisAgent:
    agent_id: str
    affect: dict[str, AffectDimension] = field(
        default_factory=lambda: {name: AffectDimension() for name in AFFECT_DIMENSIONS}
    )
    events: dict[str, dict[str, Any]] = field(default_factory=dict)
    memories: dict[str, MemoryNode] = field(default_factory=dict)
    links: dict[tuple[str, str, str], MemoryLink] = field(default_factory=dict)
    working_set: list[str] = field(default_factory=list)
    cleanup_receipts: list[dict[str, Any]] = field(default_factory=list)

    # Learning is intentionally slow relative to momentary activation.
    corr_alpha: float = 0.08
    sensitivity_rate: float = 0.015
    link_learning_rate: float = 0.05
    weak_link_decay: float = 0.995

    def observe(
        self,
        *,
        event_id: str,
        source: str,
        payload: dict[str, Any],
        tags: list[str] | None = None,
        salience: float = 0.5,
        confidence: float = 0.5,
        affect_signal: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Ingest one observation into the OHM event ledger and learn from it.

        This is deliberately conservative: the immutable event is always stored,
        while durable memory promotion is policy-driven.
        """
        if event_id in self.events:
            raise ValueError(f"duplicate event_id: {event_id}")

        salience = self._unit(salience)
        confidence = self._unit(confidence)
        tags = sorted(set(tags or []))
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        canonical_payload = self._canonical_json(payload)
        content_hash = sha256(canonical_payload).hexdigest()
        event = {
            "schema_version": "ohm.genesis.event.v1",
            "event_id": event_id,
            "observed_at": now,
            "source": source,
            "kind": "observation",
            "payload": payload,
            "salience": salience,
            "confidence": confidence,
            "tags": tags,
            "provenance": {
                "content_sha256": content_hash,
                "parent_event_ids": [],
                "producer": "ohm.genesis_agent.py",
                "producer_version": "0.1.0",
            },
        }
        self.events[event_id] = event

        self._apply_affect_signal(affect_signal or {}, salience, confidence)
        node = self._promote_observation(event)
        if node is not None:
            self._relate(node)
            self._resonate(node.node_id)

        self.recursive_clean()
        return event

    def _promote_observation(self, event: dict[str, Any]) -> MemoryNode | None:
        """Promote only observations with enough relevance to justify durable memory."""
        salience = float(event["salience"])
        confidence = float(event["confidence"])
        if max(salience, confidence) < 0.35:
            return None

        node_id = f"mem:{event['event_id']}"
        node = MemoryNode(
            node_id=node_id,
            kind="episodic",
            content=event["payload"],
            source_event_id=event["event_id"],
            confidence=confidence,
            salience=salience,
            created_at=event["observed_at"],
            last_accessed_at=event["observed_at"],
        )
        self.memories[node_id] = node
        self.working_set.append(node_id)
        self.working_set = self.working_set[-64:]
        return node

    def _relate(self, node: MemoryNode) -> None:
        """Create associative links by shared semantic surface features.

        This first agent uses tags/keys as a deliberately simple reference
        mechanism. Future runtimes can replace the similarity producer while
        preserving the same link contract.
        """
        current_features = self._features(node.content)
        for other_id, other in list(self.memories.items()):
            if other_id == node.node_id or other.quarantined:
                continue
            overlap = current_features & self._features(other.content)
            if not overlap:
                continue

            similarity = min(1.0, len(overlap) / max(1, len(current_features)))
            key = (node.node_id, other_id, "association")
            self.links[key] = MemoryLink(
                source_id=node.node_id,
                target_id=other_id,
                relation="association",
                weight=similarity,
                phase=0.0,
            )

    def _resonate(self, seed_id: str, depth: int = 3) -> None:
        """Spread activation recursively through the association graph.

        'Quantum' here is the project's metaphor: concurrent candidate states,
        phase-like coupling, signed influence, and resonance-weighted attention.
        It is not a claim of quantum hardware or literal particles.
        """
        frontier: dict[str, float] = {seed_id: 1.0}
        visited_strength: dict[str, float] = {}

        for layer in range(depth):
            next_frontier: dict[str, float] = {}
            for source_id, strength in frontier.items():
                previous = visited_strength.get(source_id, 0.0)
                if strength <= previous:
                    continue
                visited_strength[source_id] = strength

                for link in self.links.values():
                    if link.source_id != source_id:
                        continue
                    phase_gain = (math.cos(link.phase) + 1.0) / 2.0
                    propagated = strength * link.weight * phase_gain * (0.72 ** layer)
                    if propagated < 0.03:
                        continue
                    next_frontier[link.target_id] = max(
                        next_frontier.get(link.target_id, 0.0), propagated
                    )
                    link.phase = (link.phase + 0.173) % (2.0 * math.pi)
                    link.reinforced += 1
                    link.weight = min(
                        1.0,
                        link.weight + self.link_learning_rate * propagated * (1.0 - link.weight),
                    )

                    target = self.memories.get(link.target_id)
                    if target is not None:
                        target.salience = self._unit(target.salience + 0.05 * propagated)
                        target.access_count += 1
                        target.last_accessed_at = datetime.now(timezone.utc).isoformat().replace(
                            "+00:00", "Z"
                        )
            frontier = next_frontier

        ordered = sorted(visited_strength, key=visited_strength.get, reverse=True)
        self.working_set = ordered[:64]

    def _apply_affect_signal(
        self, signal: dict[str, float], salience: float, confidence: float
    ) -> None:
        for name, raw in signal.items():
            if name not in self.affect:
                continue

            dimension = self.affect[name]
            normalized = self._signed_unit(raw)
            weighted = normalized * dimension.sensitivity * salience

            # Fast state: current activation reacts immediately.
            target = self._unit(0.5 + 0.5 * weighted)
            dimension.activation = 0.65 * dimension.activation + 0.35 * target

            # Slow state: correlation EMA and learned sensitivity evolve gradually.
            evidence = normalized * confidence
            dimension.corr_ema = (
                (1.0 - self.corr_alpha) * dimension.corr_ema
                + self.corr_alpha * evidence
            )
            dimension.sensitivity += (
                self.sensitivity_rate
                * dimension.corr_ema
                * salience
                * confidence
            )
            dimension.clamp()

    def recursive_clean(self, depth: int = 3) -> None:
        """Self-heal by recursively cleaning structure while preserving receipts."""
        for _ in range(depth):
            changed = False
            changed |= self._quarantine_invalid_memories()
            changed |= self._collapse_exact_duplicates()
            changed |= self._decay_and_prune_links()
            changed |= self._repair_working_set()
            if not changed:
                break

    def _quarantine_invalid_memories(self) -> bool:
        changed = False
        for node in self.memories.values():
            invalid = not node.node_id or node.source_event_id not in self.events
            if invalid and not node.quarantined:
                node.quarantined = True
                self._cleanup_receipt("quarantine", [node.node_id], "invalid provenance")
                changed = True
        return changed

    def _collapse_exact_duplicates(self) -> bool:
        by_hash: dict[str, str] = {}
        changed = False
        for node_id in sorted(self.memories):
            node = self.memories[node_id]
            if node.quarantined or node.superseded_by is not None:
                continue
            digest = sha256(self._canonical_json(node.content)).hexdigest()
            keeper = by_hash.get(digest)
            if keeper is None:
                by_hash[digest] = node_id
                continue

            node.superseded_by = keeper
            self._redirect_links(node_id, keeper)
            self._cleanup_receipt("deduplicate", [node_id, keeper], f"content_sha256:{digest}")
            changed = True
        return changed

    def _redirect_links(self, old_id: str, new_id: str) -> None:
        rebuilt: dict[tuple[str, str, str], MemoryLink] = {}
        for link in self.links.values():
            source = new_id if link.source_id == old_id else link.source_id
            target = new_id if link.target_id == old_id else link.target_id
            if source == target:
                continue
            key = (source, target, link.relation)
            existing = rebuilt.get(key)
            if existing is None or abs(link.weight) > abs(existing.weight):
                link.source_id = source
                link.target_id = target
                rebuilt[key] = link
        self.links = rebuilt

    def _decay_and_prune_links(self) -> bool:
        changed = False
        keep: dict[tuple[str, str, str], MemoryLink] = {}
        for key, link in self.links.items():
            link.weight *= self.weak_link_decay
            if abs(link.weight) < 0.02:
                self._cleanup_receipt("prune_link", [link.source_id, link.target_id], "weak association")
                changed = True
                continue
            keep[key] = link
        self.links = keep
        return changed

    def _repair_working_set(self) -> bool:
        repaired = [
            node_id
            for node_id in self.working_set
            if node_id in self.memories
            and not self.memories[node_id].quarantined
            and self.memories[node_id].superseded_by is None
        ]
        changed = repaired != self.working_set
        self.working_set = list(dict.fromkeys(repaired))[-64:]
        if changed:
            self._cleanup_receipt("repair_working_set", self.working_set, "removed invalid references")
        return changed

    def _cleanup_receipt(self, action: str, targets: list[str], reason: str) -> None:
        self.cleanup_receipts.append(
            {
                "action": action,
                "targets": sorted(set(targets)),
                "reason": reason,
                "at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }
        )

    @staticmethod
    def _features(value: Any) -> set[str]:
        features: set[str] = set()
        if isinstance(value, dict):
            for key, child in value.items():
                features.add(str(key).strip().lower())
                features.update(OhmGenesisAgent._features(child))
        elif isinstance(value, list):
            for child in value:
                features.update(OhmGenesisAgent._features(child))
        elif isinstance(value, str):
            for token in value.lower().split():
                token = "".join(ch for ch in token if ch.isalnum() or ch in "-_'")
                if len(token) >= 3:
                    features.add(token)
        return features

    @staticmethod
    def _canonical_json(value: Any) -> bytes:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

    @staticmethod
    def _unit(value: float) -> float:
        return min(1.0, max(0.0, float(value)))

    @staticmethod
    def _signed_unit(value: float) -> float:
        return min(1.0, max(-1.0, float(value)))


if __name__ == "__main__":
    joe = OhmGenesisAgent(agent_id="joe.genesis")
    joe.observe(
        event_id="genesis-0001",
        source="manual",
        payload={
            "title": "Genesis",
            "summary": "Joe receives his first OHM observation.",
            "concepts": ["memory", "learning", "identity"],
        },
        tags=["genesis", "ohm"],
        salience=1.0,
        confidence=1.0,
        affect_signal={"curiosity": 1.0, "awe": 0.7, "resolve": 0.4},
    )

    print(
        json.dumps(
            {
                "agent_id": joe.agent_id,
                "events": len(joe.events),
                "memories": len(joe.memories),
                "links": len(joe.links),
                "working_set": joe.working_set,
                "affect": {
                    name: {
                        "activation": round(state.activation, 6),
                        "sensitivity": round(state.sensitivity, 6),
                        "corr_ema": round(state.corr_ema, 6),
                    }
                    for name, state in joe.affect.items()
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
