# Remediation Backlog (Production Hardening)

This backlog converts the audit into concrete, prioritized implementation tickets.

## Severity and Estimation Model
- Severity: Critical, High, Medium
- Estimates: person-days (pd)
- Priority bands:
  - P0: must complete before production rollout
  - P1: complete before scale-up
  - P2: quality and operability improvements

## P0 Tickets

### IO-001 - Enforce Hard-Fail CI Gates
- Severity: Critical
- Estimate: 0.5 pd
- Scope:
  - Remove non-blocking behavior for static analysis and security checks.
  - Ensure failed type/security checks fail the workflow.
- Acceptance Criteria:
  - CI fails when MyPy fails.
  - CI fails when Bandit finds issues.
  - CI fails when Safety returns vulnerabilities.
  - No `continue-on-error` or `|| true` remains in blocking jobs.
- Dependencies: none

### IO-002 - Implement Real Incremental Hash Reuse
- Severity: Critical
- Estimate: 1.5 pd
- Scope:
  - Load cached metadata/hashes and reuse unchanged file hashes.
  - Hash only files that changed (`mtime` or `size` mismatch) or cache misses.
  - Persist updated hash records in batch.
- Acceptance Criteria:
  - Second scan over unchanged folder hashes fewer files than first scan.
  - Output reports reused hash count.
  - Unit tests cover cache read and bulk write APIs.
- Dependencies: IO-001

### IO-003 - Fix Cleanup Engine Inconsistency (GUI vs Core Cleaner)
- Severity: Critical
- Estimate: 2 pd
- Scope:
  - Route GUI cleanup through core cleaner path semantics.
  - Ensure backup paths preserve structure and deterministic restore behavior.
  - Persist deletion journal to database for recoverability.
- Acceptance Criteria:
  - GUI and CLI produce equivalent backup and restore behavior.
  - Restore command can recover deleted files from persisted journal.
  - Collision handling and nested paths covered by tests.
- Dependencies: IO-002

### IO-004 - Correct Similarity Threshold Semantics
- Severity: Critical
- Estimate: 1 pd
- Scope:
  - Align GUI slider scale with comparator threshold scale.
  - Add explicit conversion between UI percentage and Hamming threshold.
  - Add bound validation in both CLI and GUI paths.
- Acceptance Criteria:
  - Same threshold intent yields same duplicate grouping in CLI and GUI.
  - Out-of-range thresholds are rejected with clear error.
  - Regression tests validate threshold mapping.
- Dependencies: none

## P1 Tickets

### IO-005 - Stream Scan Pipeline to Reduce Memory Pressure
- Severity: High
- Estimate: 3 pd
- Scope:
  - Replace full-list accumulation with bounded streaming batches.
  - Perform size grouping and hash scheduling incrementally.
- Acceptance Criteria:
  - Peak memory stays bounded on large corpus scans.
  - Functional output parity with current implementation.
  - Benchmarks included in docs.
- Dependencies: IO-002

### IO-006 - Replace O(n^2) Perceptual Comparison Strategy
- Severity: High
- Estimate: 4 pd
- Scope:
  - Introduce candidate bucketing/indexing before pairwise checks.
  - Keep exact-hash path isolated and fast.
- Acceptance Criteria:
  - Runtime growth materially improved for large candidate sets.
  - Similarity quality remains within acceptable precision/recall bounds.
  - Performance benchmark script committed.
- Dependencies: IO-005

### IO-007 - Dependency Hygiene and Runtime Slimming
- Severity: High
- Estimate: 1 pd
- Scope:
  - Keep runtime requirements strictly runtime-only.
  - Remove unused heavy dependencies from runtime set.
  - Keep metadata aligned across dependency manifests.
- Acceptance Criteria:
  - Runtime install excludes testing/lint tools.
  - Removed dependency is not imported by source.
  - Dependency manifests are consistent.
- Dependencies: none

### IO-008 - Fix Path Protection Matching
- Severity: High
- Estimate: 1 pd
- Scope:
  - Replace prefix-based protected-path checks with robust path relationship checks.
  - Handle symlink and normalization cases safely.
- Acceptance Criteria:
  - False positives from string-prefix matching are eliminated.
  - Tests include sibling and nested protected path cases.
- Dependencies: IO-003

### IO-009 - Implement/Remove Dead CLI Options
- Severity: High
- Estimate: 1 pd
- Scope:
  - Implement true `--group-id` behavior or remove option and related docs.
  - Ensure command behavior is explicit and test-covered.
- Acceptance Criteria:
  - `--group-id` has deterministic behavior verified by tests, or does not exist.
  - Help text matches actual behavior.
- Dependencies: none

## P2 Tickets

### IO-010 - Improve Test Portfolio Depth
- Severity: Medium
- Estimate: 3 pd
- Scope:
  - Add CLI integration tests.
  - Add GUI smoke tests for scan/analyze/cleanup path.
  - Add long-run and failure-injection tests.
- Acceptance Criteria:
  - Test suite includes integration tests for CLI flows.
  - GUI smoke path is validated in CI or nightly pipeline.
  - At least one destructive-path rollback scenario is tested.
- Dependencies: IO-003, IO-004

### IO-011 - Add Structured Observability
- Severity: Medium
- Estimate: 2 pd
- Scope:
  - Add structured JSON logging with operation IDs.
  - Emit counters/timers for scan/hash/compare/delete stages.
  - Define basic alert thresholds.
- Acceptance Criteria:
  - Logs include traceable operation IDs.
  - Metrics emitted for core pipeline stages.
  - Runbook documents alerts and triage.
- Dependencies: IO-005

### IO-012 - Documentation Truthfulness Pass
- Severity: Medium
- Estimate: 1 pd
- Scope:
  - Align README claims with verified implementation and benchmarks.
  - Add benchmark methodology section.
- Acceptance Criteria:
  - No unsupported scale/performance claims remain.
  - Benchmark methods and environment are documented.
- Dependencies: IO-005, IO-006

## Hardening Slice Status
- Implemented in this slice:
  - IO-001 (CI gate enforcement)
  - IO-002 (cache-read incremental hashing)
  - IO-003 (GUI cleanup unified with Cleaner + persistent deletion journal + restore command)
  - IO-004 (threshold semantics alignment between GUI percentage and comparator threshold)
  - IO-007 (dependency cleanup)
  - IO-009 (group-id removal path implemented via scan JSON input)

## Delivery Plan (Suggested)
1. Sprint 1 (P0): IO-001, IO-002, IO-004, IO-003
2. Sprint 2 (P1): IO-005, IO-006, IO-008, IO-009
3. Sprint 3 (P2): IO-010, IO-011, IO-012
