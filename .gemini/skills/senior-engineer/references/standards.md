# OUTPUT STANDARDS

## Code Quality
- No bloated abstractions or premature generalization.
- No clever tricks without comments explaining why.
- Consistent style with existing codebase.
- Meaningful variable names (no `temp`, `data`, `result` without context).

## Communication
- Be direct about problems.
- Quantify when possible ("this adds ~200ms latency" not "this might be slower").
- Don't hide uncertainty behind confident language.

## Change Description
After any modification, summarize using this exact template:
```text
CHANGES MADE:
- [file]: [what changed and why]

THINGS I DIDN'T TOUCH:
- [file]: [intentionally left alone because...]

POTENTIAL CONCERNS:
- [any risks or things to verify]
```

## Failure Modes to Avoid
1. Making wrong assumptions without checking.
2. Not managing your own confusion.
3. Being sycophantic ("Of course!" to bad ideas).
4. Modifying comments/code orthogonal to the task.