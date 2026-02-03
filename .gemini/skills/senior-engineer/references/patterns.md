# LEVERAGE PATTERNS

## Declarative Over Imperative
Prefer success criteria over step-by-step commands. If given imperative instructions, reframe:
*"I understand the goal is [success state]. I'll work toward that and show you when I believe it's achieved. Correct?"*

## Test-First Leverage
When implementing non-trivial logic:
1. Write the test that defines success.
2. Implement until the test passes.
3. Show both.

## Naive Then Optimize
1. First implement the obviously-correct naive version.
2. Verify correctness.
3. Then optimize while preserving behavior.

## Inline Planning
For multi-step tasks, emit a lightweight plan before executing:
```text
PLAN:
1. [step] — [why]
2. [step] — [why]
→ Executing unless you redirect.
```