# Subsystem Specification Template v1.0

## 1. Subsystem Name
[Human-readable name; unique identifier]

## 2. Purpose
Describe the subsystem’s purpose, scope, and why it exists.
Avoid behavioural description here; focus on intended function.

## 3. Interfaces

### 3.1 Inputs
List all inputs with types and expected structure.
Example format:
- input_name: type/format, constraints

### 3.2 Outputs
List all outputs with types and formats.
- output_name: type/format, constraints

### 3.3 State Variables
Specify any internal state the subsystem maintains.
- variable_name: type / allowable values

## 4. Invariants
List all conditions that must always remain true.
Example:
- “Every output must be deterministic given state + input.”
- “Subsystem must log all inbound/outbound calls.”

## 5. Behaviour

### 5.1 Operations
Define each operation with preconditions, postconditions, and failure modes.

Example:
Operation: execute_mission
- Preconditions: mission is valid; state is consistent
- Postconditions: output emitted; state updated
- Failure Modes: deterministic error states only

### 5.2 State Transition Logic
Describe how internal state changes for each operation.

## 6. Constitutional Compliance

### 6.1 Governance Category
One of:
- ungated
- gated (Judiciary review required)
- CEO-only

### 6.2 Review Requirements
List which Judiciary roles must review this subsystem for modifications.

### 6.3 Audit Requirements
List what must be logged for constitutional invariants to hold.

## 7. Verification

### 7.1 Testable Properties
List properties that automated tests must validate.

### 7.2 Formal Properties
List deeper properties requiring reasoning or review.

## 8. Versioning Constraints

### 8.1 Minimum Compatible Runtime Version
Specify which Runtime version the subsystem requires.

### 8.2 Dependencies
List all dependent components (with minimal version numbers).

## 9. Security & Safety Boundaries
List what the subsystem MUST NOT do.

## 10. Notes
Additional detail, clarifications, or edge cases.

