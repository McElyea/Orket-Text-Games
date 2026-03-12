from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

from .classify import classify_question
from .companion import maybe_nudge
from .render import RenderedResponse, fact_phrase_for, render_npc_response
from .resolve import resolve_answer
from .reveal import compute_reveal
from .tts import synthesize_speech
from .types import AnswerDecision, CanonicalQuery, CompanionMemory, DecisionMode, IntentId, SurfaceId, TranscriptTurn, WorldGraph


@dataclass
class GameRuntime:
    world: WorldGraph
    settings: dict[str, Any] = field(default_factory=dict)
    tts_provider: Any = None
    llm_provider: Any = None
    transcript: list[TranscriptTurn] = field(default_factory=list)
    discoveries: set[str] = field(default_factory=set)
    last_nudge_key: str | None = None
    last_nudge_turn_index: int = -999
    recent_nudge_keys: list[str] = field(default_factory=list)
    recent_attempt_keys: list[str] = field(default_factory=list)
    accused_npc_id: str | None = None
    closed: bool = False

    def ask(
        self,
        *,
        npc_id: str,
        raw_question: str,
        memory: CompanionMemory,
        forced_surface: SurfaceId | None = None,
    ) -> dict[str, Any]:
        if self.closed:
            raise RuntimeError("run_closed")
        identity = self._identity_response(raw_question, npc_id)
        if identity is not None:
            canonical = CanonicalQuery(
                intent_id=IntentId.META_REPEAT,
                surface_id=SurfaceId.SURF_META,
                confidence=1.0,
            )
            return self._finalize_turn(
                npc_id=npc_id,
                raw_question=raw_question,
                canonical=canonical,
                decision_mode="ANSWER",
                response_text=identity,
                memory=memory,
            )

        canonical = classify_question(raw_question, list(self.world.selected_npc_ids), {})
        canonical = self._apply_forced_surface(canonical, forced_surface)

        fact_id = self._fact_for_intent(canonical.intent_id.value)
        decision = resolve_answer(
            self.world,
            npc_id,
            {
                "intent_id": canonical.intent_id.value,
                "fact_id": fact_id,
                "surface_id": canonical.surface_id.value,
                "place_ref": canonical.place_ref,
                "object_id": canonical.object_id,
                "time_ref": canonical.time_ref,
            },
        )
        rendered = render_npc_response(
            world=self.world,
            npc_id=npc_id,
            canonical_query=canonical,
            decision=decision,
            scene_id=self.world.scene_template_id,
            turn_index=len(self.transcript) + 1,
        )

        if self.llm_provider is not None:
            rendered = self._try_llm_render(
                npc_id=npc_id,
                canonical=canonical,
                decision=decision,
                raw_question=raw_question,
                template_rendered=rendered,
            )

        turn = TranscriptTurn(
            timestamp=int(time.time() * 1000),
            npc_id=npc_id,
            raw_question=raw_question,
            canonical_query=canonical,
            decision=decision.mode,
            npc_response_text=rendered.text,
            companion_line=None,
        )
        self.transcript.append(turn)
        discovery_grew = self._record_discoveries(canonical=canonical, decision=decision)
        nudge = self._maybe_companion_line(
            npc_id=npc_id,
            canonical=canonical,
            decision=decision,
            memory=memory,
            discovery_grew=discovery_grew,
        )
        if nudge:
            self.transcript[-1] = TranscriptTurn(
                timestamp=turn.timestamp,
                npc_id=turn.npc_id,
                raw_question=turn.raw_question,
                canonical_query=turn.canonical_query,
                decision=turn.decision,
                npc_response_text=turn.npc_response_text,
                companion_line=nudge,
            )
            self.last_nudge_key = self._normalize_question(nudge)
            self.last_nudge_turn_index = len(self.transcript)
            self.recent_nudge_keys.append(self.last_nudge_key)
            if len(self.recent_nudge_keys) > 6:
                self.recent_nudge_keys = self.recent_nudge_keys[-6:]
        synth = synthesize_speech(rendered.text, rendered.audio_hint, self.tts_provider)
        return {
            "canonical_query": canonical,
            "decision": decision,
            "npc_response_text": rendered.text,
            "companion_line": nudge,
            "audio_hint": rendered.audio_hint,
            "synth_result": synth,
        }

    def _try_llm_render(
        self,
        *,
        npc_id: str,
        canonical: CanonicalQuery,
        decision: AnswerDecision,
        raw_question: str,
        template_rendered: Any,
    ) -> Any:
        """Attempt LLM-backed rendering, fall back to template on failure."""
        from .llm_render import render_via_llm
        from .render import _prompt_cfg

        fact_phrase_text = None
        if decision.fact_id and decision.fact_id in self.world.facts:
            fact = self.world.facts[decision.fact_id]
            fact_phrase_text = fact_phrase_for(
                fact_type=fact.fact_type,
                fact_value=fact.value,
                scene_id=self.world.scene_template_id,
                npc_id=npc_id,
                turn_index=len(self.transcript) + 1,
            )

        time_budget = int(self.settings.get("llm_time_budget_ms", 2000))
        llm_result = render_via_llm(
            llm_provider=self.llm_provider,
            world=self.world,
            npc_id=npc_id,
            canonical_query=canonical,
            decision=decision,
            raw_question=raw_question,
            fact_phrase=fact_phrase_text,
            prompt_config=_prompt_cfg(),
            turn_index=len(self.transcript) + 1,
            template_fallback=template_rendered.text,
            time_budget_ms=time_budget,
        )
        return RenderedResponse(text=llm_result.text, audio_hint=template_rendered.audio_hint)

    def accuse(self, *, accused_npc_id: str) -> dict[str, Any]:
        if self.closed:
            raise RuntimeError("run_closed")
        self.accused_npc_id = accused_npc_id
        self.closed = True
        reveal = compute_reveal(self.world, accused_npc_id=accused_npc_id)
        won = accused_npc_id == self.world.culprit_npc_id
        return {
            "outcome": "win" if won else "lose",
            "reveal": reveal,
        }

    @staticmethod
    def _fact_for_intent(intent_id: str) -> str | None:
        mapping = {
            "WHEN_WAS": "FACT_TIME_ANCHOR_1",
            "WHERE_WAS": "FACT_PRESENCE_1",
            "DID_YOU_HAVE_ACCESS": "FACT_ACCESS_ANCHOR_1",
            "WHO_HAD_ACCESS": "__ACCESS_LIST__",
            "DID_YOU_SEE": "FACT_WITNESS_1",
            "WHO_WAS_WITH": "FACT_WITNESS_1",
            "DID_YOU_DO": "FACT_OBJECT_MOVED_1",
        }
        return mapping.get(intent_id)

    def _apply_forced_surface(self, canonical: CanonicalQuery, forced_surface: SurfaceId | None) -> CanonicalQuery:
        if forced_surface is None:
            return canonical
        forced_intent = {
            SurfaceId.SURF_TIME: IntentId.WHEN_WAS,
            SurfaceId.SURF_LOCATION: IntentId.WHERE_WAS,
            SurfaceId.SURF_ACCESS: IntentId.WHO_HAD_ACCESS,
            SurfaceId.SURF_WITNESS: IntentId.DID_YOU_SEE,
        }.get(forced_surface, canonical.intent_id)
        return CanonicalQuery(
            intent_id=forced_intent,
            surface_id=forced_surface,
            subject_id=canonical.subject_id,
            object_id=canonical.object_id,
            time_ref=canonical.time_ref,
            place_ref=canonical.place_ref,
            polarity=canonical.polarity,
            confidence=max(canonical.confidence, 0.75),
            raw_text_hash=canonical.raw_text_hash,
        )

    def _identity_response(self, raw_question: str, npc_id: str) -> str | None:
        lower = str(raw_question or "").strip().lower()
        triggers = {"what's your name", "what is your name", "who are you", "your name"}
        if not any(token in lower for token in triggers):
            return None
        return npc_id.replace("_", " ").title()

    def _finalize_turn(
        self,
        *,
        npc_id: str,
        raw_question: str,
        canonical: CanonicalQuery,
        decision_mode: str,
        response_text: str,
        memory: CompanionMemory,
    ) -> dict[str, Any]:
        from .types import AnswerDecision, DecisionMode

        decision = AnswerDecision(mode=DecisionMode(decision_mode), fact_id=None)
        turn = TranscriptTurn(
            timestamp=int(time.time() * 1000),
            npc_id=npc_id,
            raw_question=raw_question,
            canonical_query=canonical,
            decision=decision.mode,
            npc_response_text=response_text,
            companion_line=None,
        )
        self.transcript.append(turn)
        discovery_grew = self._record_discoveries(canonical=canonical, decision=decision)
        nudge = self._maybe_companion_line(
            npc_id=npc_id,
            canonical=canonical,
            decision=decision,
            memory=memory,
            discovery_grew=discovery_grew,
        )
        if nudge:
            self.transcript[-1] = TranscriptTurn(
                timestamp=turn.timestamp,
                npc_id=turn.npc_id,
                raw_question=turn.raw_question,
                canonical_query=turn.canonical_query,
                decision=turn.decision,
                npc_response_text=turn.npc_response_text,
                companion_line=nudge,
            )
            self.last_nudge_key = self._normalize_question(nudge)
            self.last_nudge_turn_index = len(self.transcript)
            self.recent_nudge_keys.append(self.last_nudge_key)
            if len(self.recent_nudge_keys) > 6:
                self.recent_nudge_keys = self.recent_nudge_keys[-6:]
        return {
            "canonical_query": canonical,
            "decision": decision,
            "npc_response_text": response_text,
            "companion_line": nudge,
        }

    def _record_discoveries(self, *, canonical: CanonicalQuery, decision: Any) -> bool:
        before = len(self.discoveries)
        if canonical.place_ref:
            self.discoveries.add(f"disc:place:{canonical.place_ref}")
        if canonical.object_id:
            self.discoveries.add(f"disc:object:{canonical.object_id}")
        if canonical.subject_id:
            self.discoveries.add(f"disc:npc:{canonical.subject_id}")
        if decision is None:
            return len(self.discoveries) > before
        fact_id = str(getattr(decision, "fact_id", "") or "").strip()
        if fact_id and not fact_id.startswith("__"):
            self.discoveries.add(f"disc:fact:{fact_id}")
            fact = self.world.facts.get(fact_id)
            payload = fact.value if (fact is not None and isinstance(fact.value, dict)) else {}
            if isinstance(payload, dict):
                who = str(payload.get("who", "")).strip()
                where = str(payload.get("where", "")).strip()
                obj = str(payload.get("object", "")).strip()
                witness = str(payload.get("witness", "")).strip()
                npc = str(payload.get("npc", "")).strip()
                for npc_id in (who, witness, npc):
                    if npc_id:
                        self.discoveries.add(f"disc:npc:{npc_id}")
                if where:
                    self.discoveries.add(f"disc:place:{where}")
                if obj:
                    self.discoveries.add(f"disc:object:{obj}")
        return len(self.discoveries) > before

    def _guided_nudge(self, *, npc_id: str, canonical: CanonicalQuery, decision: Any) -> str | None:
        candidates = self._guided_nudge_candidates(npc_id=npc_id, canonical=canonical, decision=decision)
        recent = {self._normalize_question(t.raw_question) for t in self.transcript[-4:]}
        recent_cores = {self._question_core(t.raw_question) for t in self.transcript[-4:]}
        for _, suggestion in candidates:
            if not self._suggestion_collides(suggestion, recent, recent_cores):
                return suggestion
        for _, suggestion in candidates:
            return suggestion
        return None

    def _guided_nudge_candidates(self, *, npc_id: str, canonical: CanonicalQuery, decision: Any) -> list[tuple[str | None, str]]:
        candidates: list[tuple[str | None, str]] = []
        kind = self._turn_yielded_kind(decision=decision)
        place_hint = canonical.place_ref or "SERVICE_DOOR"
        place_text = place_hint.replace("_", " ").lower()

        if str(getattr(decision, "mode", "")) == DecisionMode.ANSWER.value:
            if kind == "witness":
                candidates.extend(
                    [
                        (None, f'Try: "Who can confirm who was at the {place_text}?"  Then: "Who had access to the {place_text}?"'),
                        (f"disc:place:{place_hint}", f'Try: "Where were you at 11:03 near the {place_text}?"  Then: "Who had access to the {place_text}?"'),
                    ]
                )
            elif kind == "presence":
                candidates.extend(
                    [
                        (None, f'Try: "Who can confirm that at the {place_text}?"  Then: "Who had access to the {place_text}?"'),
                        (f"disc:place:{place_hint}", f'Try: "Who did you see near the {place_text}?"  Then: "Who had access to the {place_text}?"'),
                    ]
                )
            elif kind == "action":
                candidates.extend(
                    [
                        ("disc:object:AUDIT_DRIVE", 'Try: "What do you know about the audit drive?"  Then: "Who had access to the service door?"'),
                        (None, 'Try: "Who can confirm that action?"  Then: "Where were you at 11:03?"'),
                    ]
                )

        if str(getattr(decision, "mode", "")).endswith("REFUSE") and canonical.intent_id in {
            IntentId.DID_YOU_SEE,
            IntentId.WHO_WAS_WITH,
        }:
            candidates.extend(
                [
                    ("disc:place:SERVICE_DOOR", 'Try: "Who had access to the service door?"  Then: "When were you at 11:03?"'),
                    (None, 'Try: "Where were you at 11:03?"  Then: "Who can confirm that?"'),
                ]
            )
        elif str(getattr(decision, "mode", "")).endswith("DONT_KNOW"):
            candidates.extend(
                [
                    (None, 'Try: "Who did you see near the service door?"  Then: "Who had access to the service door?"'),
                    (None, 'Try: "Where were you at 11:03?"  Then: "When did the alarm hit?"'),
                ]
            )
        elif str(getattr(decision, "mode", "")).endswith("ANSWER") and canonical.intent_id in {
            IntentId.DID_YOU_SEE,
            IntentId.WHO_WAS_WITH,
        }:
            candidates.extend(
                [
                    ("disc:place:SERVICE_DOOR", 'Try: "Who had access to the service door?"  Then: "Where were you at 11:03?"'),
                    (None, 'Try: "Who can confirm that?"  Then: "Who had access to the service door?"'),
                ]
            )

        unknown: list[str] = []
        lead_order = ("LEAD_WITNESS_1", "LEAD_PRESENCE_1", "LEAD_OBJECT_1", "LEAD_ACTION_1")
        for lead_id in lead_order:
            if lead_id not in self.world.lead_unlocks:
                continue
            for key in self.world.lead_unlocks.get(lead_id, ()):
                if key not in self.discoveries and key not in unknown:
                    unknown.append(key)
        for target in unknown:
            hinted_marker = f"disc:hint:{target}"
            if hinted_marker in self.discoveries:
                continue
            if target.startswith("disc:place:SERVICE_DOOR"):
                if self._npc_can_answer_access(npc_id=npc_id):
                    candidates.append((target, 'Try: "Who had access to the service door?"  Then: "Did you have access to the service door?"'))
                else:
                    access_npc = self._find_access_npc(exclude_npc_id=npc_id)
                    if access_npc:
                        display = access_npc.replace("_", " ").title()
                        candidates.append((target, f'Try asking {display}: "Who had access to the service door?"  Then ask here: "Where were you at 11:03?"'))
            elif target.startswith("disc:place:BOARDROOM"):
                candidates.append((target, 'Try: "Who was near the boardroom?"  Then: "When were you in the boardroom?"'))
            elif target.startswith("disc:place:ARCHIVE"):
                if self._npc_can_answer_access(npc_id=npc_id):
                    candidates.append((target, 'Try: "Who had access to the archive?"  Then: "Where were you near the archive?"'))
                else:
                    access_npc = self._find_access_npc(exclude_npc_id=npc_id)
                    if access_npc:
                        display = access_npc.replace("_", " ").title()
                        candidates.append((target, f'Try asking {display}: "Who had access to the archive?"  Then ask here: "Where were you near the archive?"'))
            elif target.startswith("disc:object:AUDIT_DRIVE"):
                candidates.append((target, 'Try: "What do you know about the audit drive?"  Then: "Did you move the audit drive?"'))
            elif target.startswith("disc:object:BOARDROOM_FEED"):
                candidates.append((target, 'Try: "What do you know about the boardroom feed?"  Then: "Who was near the boardroom?"'))
            elif target.startswith("disc:fact:FACT_WITNESS_1"):
                candidates.append((target, 'Try: "Who did you see near the service door?"  Then: "Who was with you at 11:03?"'))
            elif target.startswith("disc:fact:FACT_PRESENCE_1"):
                candidates.append((target, 'Try: "Where were you at 11:03?"  Then: "Who can confirm that?"'))
            elif target.startswith("disc:fact:FACT_OBJECT_MOVED_1"):
                candidates.append((target, 'Try: "Did you move the audit drive?"  Then: "What do you know about the audit drive?"'))
        return candidates

    @staticmethod
    def _normalize_question(text: str) -> str:
        lowered = str(text or "").strip().lower()
        lowered = lowered.strip('"').strip("'").strip("`")
        cleaned = re.sub(r"[^a-z0-9\s]", " ", lowered)
        return " ".join(cleaned.split())

    @staticmethod
    def _question_core(text: str) -> str:
        tokens = re.findall(r"[a-z0-9]+", str(text or "").lower())
        stop = {
            "the",
            "a",
            "an",
            "at",
            "to",
            "of",
            "and",
            "or",
            "you",
            "your",
            "did",
            "do",
            "were",
            "was",
            "is",
            "are",
            "that",
            "there",
            "then",
        }
        core = [token for token in tokens if token not in stop]
        return " ".join(core[:5])

    def _suggestion_collides(self, suggestion: str, recent: set[str], recent_cores: set[str]) -> bool:
        lowered = suggestion.lower()
        if '"' not in lowered:
            return False
        parts = lowered.split('"')
        quoted = [self._normalize_question(parts[i]) for i in range(1, len(parts), 2)]
        quoted_cores = [self._question_core(q) for q in quoted]
        if any(q and q in recent for q in quoted):
            return True
        return any(core and core in recent_cores for core in quoted_cores)

    def _select_nudge(self, *, npc_id: str, canonical: CanonicalQuery, decision: Any, fallback: str) -> str:
        candidates = self._guided_nudge_candidates(npc_id=npc_id, canonical=canonical, decision=decision)
        kind = self._turn_yielded_kind(decision=decision)
        on_chain_only = (
            str(getattr(decision, "mode", "")) == DecisionMode.ANSWER.value
            and kind in {"witness", "presence", "action"}
            and bool(candidates)
        )
        has_fallback = any(text == fallback for _, text in candidates)
        if fallback and not has_fallback and not on_chain_only:
            candidates.append((None, fallback))
        if not candidates:
            return fallback

        recent = {self._normalize_question(t.raw_question) for t in self.transcript[-4:]}
        recent_cores = {self._question_core(t.raw_question) for t in self.transcript[-4:]}
        recent_nudges = set(self.recent_nudge_keys[-4:])

        for target, candidate in candidates:
            key = self._normalize_question(candidate)
            too_soon_repeat = (
                self.last_nudge_key is not None
                and key == self.last_nudge_key
                and (len(self.transcript) - self.last_nudge_turn_index) <= 2
            )
            if too_soon_repeat:
                continue
            if key in recent_nudges:
                continue
            if self._suggestion_collides(candidate, recent, recent_cores):
                continue
            if target:
                self.discoveries.add(f"disc:hint:{target}")
            return candidate

        for target, candidate in candidates:
            key = self._normalize_question(candidate)
            too_soon_repeat = (
                self.last_nudge_key is not None
                and key == self.last_nudge_key
                and (len(self.transcript) - self.last_nudge_turn_index) <= 2
            )
            if not too_soon_repeat:
                if key in recent_nudges:
                    continue
                if target:
                    self.discoveries.add(f"disc:hint:{target}")
                return candidate
        fallback_text = candidates[0][1]
        target = candidates[0][0]
        if target:
            self.discoveries.add(f"disc:hint:{target}")
        return fallback_text

    def _maybe_companion_line(
        self,
        *,
        npc_id: str,
        canonical: CanonicalQuery,
        decision: Any,
        memory: CompanionMemory,
        discovery_grew: bool,
    ) -> str | None:
        fallback = maybe_nudge(self.transcript, self.settings, memory)
        if not fallback:
            return None
        if not self._should_emit_nudge(decision=decision, discovery_grew=discovery_grew):
            return None
        return self._select_nudge(npc_id=npc_id, canonical=canonical, decision=decision, fallback=fallback)

    def _should_emit_nudge(self, *, decision: Any, discovery_grew: bool) -> bool:
        try:
            min_gap = max(1, int(self.settings.get("nudge_min_gap", 3)))
        except (TypeError, ValueError):
            min_gap = 3
        turns_since_last = len(self.transcript) - self.last_nudge_turn_index
        mode_raw = str(getattr(decision, "mode", ""))
        if discovery_grew:
            return True
        if turns_since_last >= min_gap:
            return True
        if mode_raw == DecisionMode.REFUSE.value and self._has_undiscovered_leads():
            return True
        return False

    def _has_undiscovered_leads(self) -> bool:
        for _, targets in self.world.lead_unlocks.items():
            for target in targets:
                if target not in self.discoveries:
                    return True
        return False

    def _turn_yielded_kind(self, *, decision: Any) -> str | None:
        fact_id = str(getattr(decision, "fact_id", "") or "").strip()
        if not fact_id or fact_id.startswith("__"):
            return None
        fact = self.world.facts.get(fact_id)
        if fact is None:
            return None
        payload = fact.value if isinstance(fact.value, dict) else {}
        if isinstance(payload, dict):
            kind = str(payload.get("kind", "")).strip().lower()
            if kind:
                return kind
        return str(getattr(fact, "fact_type", "") or "").strip().lower() or None

    def _npc_can_answer_access(self, *, npc_id: str) -> bool:
        knowledge = self.world.npc_knowledge.get(npc_id, set())
        guards = self.world.npc_guards.get(npc_id, set())
        return "FACT_ACCESS_ANCHOR_1" in knowledge and "FACT_ACCESS_ANCHOR_1" not in guards

    def _find_access_npc(self, *, exclude_npc_id: str) -> str | None:
        for candidate in self.world.selected_npc_ids:
            if candidate == exclude_npc_id:
                continue
            if self._npc_can_answer_access(npc_id=candidate):
                return candidate
        return None
