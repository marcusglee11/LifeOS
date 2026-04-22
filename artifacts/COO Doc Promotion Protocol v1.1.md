Doc Promotion Protocol v1.1

Status: Draft
Owner: COO
Purpose: Define how reviewed or ratified documents are promoted into canonical repository state without losing semantic fidelity or bypassing governance.

1. Core principle

A document does not become canonical because it is useful, well-written, or approved in chat.

A document becomes canonical only through a governed promotion flow that:
- classifies the artefact correctly,
- selects the repository by semantics,
- creates a durable work order,
- lands through a reviewable repo change,
- records the resulting authority state.

2. Promotion invariant

All document promotions must cross this authority boundary:

advisory artefact -> classification -> work order -> governance/stewardship checks -> PR-based landing -> merge/receipt -> canonical state

No external document, chat message, or draft file is itself canonical repo state.

3. Artefact classification

Before any landing work begins, classify the artefact.

### 3.1 Allowed classes

- operational state
- programme architecture / canon
- shared reusable standard / schema / contract
- governance ruling / protected artefact

### 3.2 Classification rule

Classification is semantic, not convenience-based.

The question is not “where is it easiest to put this?”
The question is “what kind of artefact is this, and what authority surface should own it?”

4. Repository selection

Select the target repository from the artefact class.

- operational state -> lifeos-operational-bus
- programme architecture / canon -> LifeOS
- shared reusable standard / schema / contract -> lifeos-common-hub

### 4.1 Repository rule

Repository choice must be justified by artefact semantics.

“Put it where we’re already working” is not a valid reason.

5. Authority check

Before promotion, determine whether the artefact is actually eligible to become canonical.

### 5.1 Questions to answer

- Is this artefact reviewed, ratified, approved, or still exploratory?
- Is authority status explicit or merely implied?
- Is there already a canonical artefact covering this same surface?
- Is the proposed landing a new canon, a replacement, a supplement, or an extraction?

### 5.2 Authority rule

No artefact may be promoted into canon unless its authority status is explicit enough for the target surface.

A “good draft” is not automatically a canonical document.

6. Work order requirement

Every document landing starts as a structured work order in lifeos-operational-bus.

### 6.1 Minimum work order contents

The work order must record:
- source artefact
- intended canonical repository
- intended path or candidate surfaces
- artefact classification
- authority status
- semantic constraints
- escalation boundary
- acceptance criteria
- supersession or duplication expectations

### 6.2 Work order rule

No direct canonical repo landing from chat.

Chat may authorize preparation, but canonical landing must be governed by a durable operational work order.

7. Governance and stewardship checks

Before content import or editing, inspect all relevant controls.

### 7.1 Required checks

- protected paths
- stewardship requirements
- indexing/update obligations
- review-packet or ruling requirements
- doc ownership conventions
- repository-local constraints

### 7.2 Governance rule

If the chosen surface is protected, the protected-path protocol governs.

Do not improvise around protected surfaces.

8. Supersession and duplication check

Before landing, determine how the artefact relates to existing canon.

### 8.1 Required outcomes

The landing must explicitly declare one of:
- new canonical artefact
- replacement / supersession
- supplement
- extraction of reusable component

### 8.2 Supersession rule

Every promotion must state its relationship to existing canon.

No silent duplication.
No accidental parallel canon.

9. Semantic fidelity rule

Promotion may normalize format, but must not silently rewrite meaning.

### 9.1 Allowed without extra approval

- markdown cleanup
- heading normalization
- link cleanup
- typo repair
- obvious formatting repair
- repository-local metadata or index hookups

### 9.2 Not allowed without explicit approval

- architectural reinterpretation
- scope changes
- policy changes
- splitting one artefact into multiple canonical artefacts
- merging separate artefacts into one
- converting document type for stylistic reasons alone

### 9.3 Fidelity rule

Format may change.
Meaning may not.

10. Landing mechanism

Canonical landing happens through a PR, not by informal dump.

### 10.1 PR must include

- canonical target path
- why this repository and surface were chosen
- source artefact reference
- originating work order reference
- authority basis for promotion
- supersession relationship
- note of any non-trivial edits
- note of any extracted follow-on artefacts or tasks

### 10.2 Promotion rule

The PR is the promotion event.
Chat approval alone is not the durable state change.

11. Merge and closure

After PR creation and merge, close the loop operationally.

### 11.1 Required closure actions

- update work order with result
- record durable canonical home
- record PR and merge references
- emit promotion or completion receipt
- open follow-on tasks for extracted standards, schemas, or shared components if needed

### 11.2 Closure rule

One artefact may produce multiple follow-on promotions, but each follow-on must be tracked separately.

12. Future-state COO automation

In the mature state, the COO should execute this flow with minimal manual prompting.

### 12.1 Expected automated loop

1. detect reviewed or ratified artefact
2. classify artefact
3. determine authority eligibility
4. choose repository and candidate surface
5. open work order
6. run governance and supersession checks
7. dispatch steward EA
8. verify PR and landing fidelity
9. record receipt and close work order

### 12.2 Automation rule

Automation may accelerate the protocol, but must not bypass it.

13. Non-goals

This protocol does not:
- decide substantive architecture correctness
- replace governance rulings
- allow chat to bypass repo controls
- permit convenience-based repo choice
- collapse multiple canonical promotions into one untracked action

14. Summary rules

1. Repo choice is semantic, not convenience-based.
2. No canonical landing without a work order.
3. Governance checks happen before content edits.
4. Supersession must be explicit.
5. Format may change; meaning may not.
6. PR is the promotion event.
7. Merge plus receipt establishes canonical landing.
8. Follow-on extractions become separate tracked promotions.

If you want, next step I can do one of three things:
1. tighten this into a shorter v1,
2. make it more constitutional and formal,
3. stress-test it with edge cases.
