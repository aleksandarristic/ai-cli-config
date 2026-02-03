---
name: go-performance-triage
description: Diagnose performance problems in Go repos using evidence-driven hypotheses and minimal-risk fixes.
---

## Rules
- Do not optimize blindly.
- Start with low-cost evidence: timing logs, counters, pprof hooks.
- Identify whether bottleneck is CPU, I/O, lock contention, or algorithmic complexity.
- Propose minimal changes first; avoid architectural rewrites unless necessary.

## Output
- Bottleneck hypotheses ranked by likelihood
- Minimal instrumentation plan
- First safe optimization patch (diff-first)
- Validation steps and rollback plan
