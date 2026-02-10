# LifeOS QuickStart Guide

<!-- LIFEOS_TODO[P1][area: docs/QUICKSTART.md][exit: context scan complete + status change to ACTIVE + DAP validate] Finalize QUICKSTART v1.0: Complete context scan pass, remove WIP/Provisional markers -->

**Status**: Active
**Authority**: COO Operating Contract v1.0
**Effective**: 2026-01-27

---

## 1. Introduction

Welcome to LifeOS. This guide provides the minimum steps required to bootstrap a new agent or human operator into the repository.

---

## 2. Prerequisites

- **Python 3.11+**
- **Git**
- **OpenRouter API Key** (for agentic operations)
- **Visual Studio Code** (recommended)

---

## 3. First Steps

### 3.1 Clone the Repository

```bash
git clone <repo-url>
cd LifeOS
```

### 3.2 Initialize Environment

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 3.3 Verify Readiness

Run the preflight check to ensure all invariants are met:

```bash
python docs/scripts/check_readiness.py
```

---

## 4. Understanding the Core

The repo is organized by Tiers:

- **Foundations**: Core principles and Constitution.
- **Governance**: Contracts, protocols, and rulings.
- **Runtime**: Implementation and mission logic.

Always check [docs/INDEX.md](../INDEX.md) for the latest navigation map.

---

## 5. Working with Protocols

All changes MUST follow the **Deterministic Artefact Protocol (DAP) v2.0**:

1. Create a Plan.
2. Get Approval.
3. Execute.
4. Verify & Steward.

---

**END OF GUIDE**
