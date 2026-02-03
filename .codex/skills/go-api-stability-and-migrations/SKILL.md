---
name: go-api-stability-and-migrations
description: Evolve internal/public Go APIs safely using deprecations, adapters, and incremental migrations.
---

## Principles
- Preserve external contracts by default.
- Introduce new API alongside old; deprecate with clear notices.
- Provide adapters/shims to keep callers working.
- Remove old API only when migration is complete.

## Output
- Contract summary (what must not break)
- Migration plan (phased)
- Minimal initial patch (new API + adapter)
- Deprecation notes and tests
