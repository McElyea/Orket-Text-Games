# Live Endpoint Contract (TS-LIVE)

Primary domain: engine
Related domains: strategy

## Routes
- `POST /textmystery/parity-check`
- `POST /textmystery/leak-check`

## POST /textmystery/parity-check

Request:
- `run_header`: `{seed, scene_id, npc_ids, difficulty, content_version, generator_version}`
- `transcript_inputs`: ordered turn entries with either:
  - question turn: `{turn, npc_id, raw_question}`
  - accusation turn: `{turn, accuse: {npc_id}}`

Response:
- `world_digest`
- `turn_results`: list of turn rows with:
  - `turn`
  - `canonical_query`: `{intent_id, surface_id, confidence, raw_text_hash}`
  - `decision` (`ANSWER|REFUSE|DONT_KNOW`)
  - `fact_id` (nullable)
  - `npc_response_text`
  - `companion_line` (nullable)
- `accusation_result`: `{accused_npc_id, outcome: WIN|LOSE, reveal_digest}`

## POST /textmystery/leak-check

Request:
- `allowed_entities: string[]`
- `allowed_fact_values: string[]`
- `text: string`

Response:
- `ok: bool`
- `violations: [] | [{type, span:{start,end}, token}]`

Violation types:
- `NEW_ENTITY`
- `NEW_FACT_VALUE`
- `DISALLOWED_PATTERN`

## Local Dev Server
- Run:
  - `python -m textmystery.cli.live_server --host 127.0.0.1 --port 8787`
- Then run live tests with:
  - `TEXTMYSTERY_RUN_LIVE=1`
  - `TEXTMYSTERY_ORKET_BASE_URL=http://127.0.0.1:8787`
  - `python -m pytest -m ts_live`
