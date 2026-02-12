---
description: Run diff-first review-fix workflow. Reads reviewer commit diff first, applies obvious/patterned fixes, and emits compact report sections.
---

Invoke the lifeos-workflow:review-fix skill and follow it exactly as presented.

If the user does not provide a reviewer commit, ask for either:
- reviewer commit SHA, or
- commit range (`<base>..<head>`), or
- branch to review against `main`.

