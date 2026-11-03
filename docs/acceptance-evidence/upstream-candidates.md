# Krita upstream change report

- Baseline: 66875f06e2874b28daa8b449c4ff16569e5c2ab5
- Target: efeeeb5fef71dca75143dae58578299b2a934265
- Classification: heuristic; source-only, not tested

## Candidate API changes

### signature_or_implementation_changed: paintLine

- File: libs/libkis/Node.h
- Evidence: source_seen
- Priority: high
- Source: https://invent.kde.org/graphics/krita/-/blob/efeeeb5fef71dca75143dae58578299b2a934265/libs/libkis/Node.h
- Line: void paintLine(int x, int y);
- Suggested: Check API presence/signature on Stable and Next, then run isolated behavior test

### added: paintPolylineStroke

- File: libs/libkis/Node.h
- Evidence: source_seen
- Priority: high
- Source: https://invent.kde.org/graphics/krita/-/blob/efeeeb5fef71dca75143dae58578299b2a934265/libs/libkis/Node.h
- Line: void paintPolylineStroke(int count);
- Suggested: Check API presence/signature on Stable and Next, then run isolated behavior test

## Changed paths

- libs/libkis/Node.h

## Relevant commits

- efeeeb5 feature
