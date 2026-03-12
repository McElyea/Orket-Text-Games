# Classification Micro-Spec (v1)

Primary domain: engine
Related domains: gameplay

## CanonicalQuery Shape
`{intent_id, surface_id, subject_id?, object_id?, time_ref?, place_ref?, polarity?, confidence, raw_text_hash}`

- `surface_id` is required and always set.
- Use `SURF_UNKNOWN` for unclassifiable inputs.

## Intent Set
- `WHERE_WAS`
- `WHEN_WAS`
- `DID_YOU_SEE`
- `DID_YOU_HAVE_ACCESS`
- `DID_YOU_DO`
- `WHO_HAD_ACCESS`
- `WHO_WAS_WITH`
- `WHAT_DO_YOU_KNOW_ABOUT`
- `META_REPEAT`
- `UNCLASSIFIED_AMBIGUOUS`

## Surface Set
- `SURF_TIME`
- `SURF_ACCESS`
- `SURF_LOCATION`
- `SURF_WITNESS`
- `SURF_OBJECT`
- `SURF_RELATIONSHIP`
- `SURF_MOTIVE`
- `SURF_ALIBI`
- `SURF_META`
- `SURF_UNKNOWN`

## Priority and Tie-Break
Apply intent priority bands first:
1. time anchored: `WHEN_WAS`, `WHERE_WAS`
2. access: `DID_YOU_HAVE_ACCESS`, `WHO_HAD_ACCESS`
3. witness: `DID_YOU_SEE`, `WHO_WAS_WITH`
4. action: `DID_YOU_DO`
5. surface: `WHAT_DO_YOU_KNOW_ABOUT`

If tied after priority:
1. lexicographically smallest `intent_id`
2. lexicographically smallest `surface_id`
3. lexicographically smallest `object_id` (or empty first)

## Confidence Rules
- Confidence range: `[0.0, 1.0]`
- Confidence is classifier-only and must not depend on world state, transcript state, or NPC response.
- `UNCLASSIFIED_AMBIGUOUS` uses `confidence=0.0`.

## Surface Probe Safety Rule
`WHAT_DO_YOU_KNOW_ABOUT` is a navigation probe only.
It must not reveal new fact IDs, undiscovered entities, or undiscovered specific values.
