# Golden Fixtures

Goldens are deterministic artifacts keyed by input tuples such as:
- scene id
- npc set
- seed
- difficulty/settings profile

Expected golden types:
- `worldgraph.json` snapshots
- `revealgraph.json` snapshots
- optional `transcript.json` snapshots

Usage:
- Normal test mode compares generated output to existing goldens.
- Set `UPDATE_GOLDENS=1` to update/create golden files intentionally.

Keep snapshots minimal, stable, and canonicalized.
