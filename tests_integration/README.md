# Integration Test Notes

These tests execute live TextMystery integration behavior against an Orket runtime boundary.

Environment controls:
- `TEXTMYSTERY_RUN_LIVE=1` enables integration tests.
- `TEXTMYSTERY_ORKET_BASE_URL=http://127.0.0.1:PORT` points to live Orket API.

Default behavior is to skip integration tests when live mode is not enabled.

Purpose:
- Validate parity between scaffold/unit contracts and live runtime contracts.
- Keep unit tests fast while preserving integration confidence.
