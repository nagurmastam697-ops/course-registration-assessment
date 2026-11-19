# Course Waitlist — AI-Assisted Engineering Assessment

## Scope
A thread-safe, in-memory service for one course offering. It supports enrollment, dropping, and one-seat FIFO waitlist promotion. There is no frontend, database, catalog, authentication, or deployment layer.

## Assumptions and policy
- A learner is eligible only when `required_prerequisite` appears in `completed_prerequisites`.
- A learner may have only one state for this offering: enrolled or waitlisted.
- Duplicate requests are idempotent in effect: they return `duplicate` and do not add another record.
- Ineligible learners are rejected at initial enrollment. If a learner already waiting becomes ineligible before promotion (for example, prerequisite data changes upstream), promotion scans in FIFO order, skips that learner, promotes the earliest currently eligible learner, and retains the skipped learner in their original queue position. This is a deliberate skip-and-retain policy.
- Capacity is a positive integer. One successful drop can open at most one seat and therefore promotes at most one learner.
- The service lock serializes each state-changing operation. This is suitable for a single process only; it is not a distributed lock or durable transaction.

## Service boundary and data/API design
`CourseRegistrationService(course_id, capacity, required_prerequisite)` exposes:
- `enroll(Learner) -> Result`: `enrolled`, `waitlisted`, `duplicate`, `ineligible`, or `invalid`.
- `drop(learner_id) -> Result`: `dropped`, `dropped_and_promoted`, `not_enrolled`, or `invalid`.
- `snapshot() -> dict`: read-only snapshot values for inspection.

`Learner` contains `learner_id` and a set/frozenset of completed prerequisite course IDs. `Result` contains a stable status, human-readable message, and optional promoted learner ID.

## Invariants
1. Enrolled count never exceeds capacity.
2. No learner appears more than once in the waitlist.
3. No learner is simultaneously enrolled and waitlisted.
4. Only eligible learners are enrolled or promoted.
5. A successful drop removes exactly one enrolled learner; promotion fills no more than the seat opened.

## Concurrency and persistence
A re-entrant mutex protects validation-dependent state transitions, duplicate checks, enrollment/drop, promotion, and snapshots. This prevents concurrent duplicate enrollment and over-capacity writes within one process. State is in memory and is lost when the process exits. A production database implementation should perform drop plus promotion in one transaction, lock the offering/queue rows, and use a uniqueness constraint on `(offering_id, learner_id)`.

## Setup and run
Requires Python 3.10+; no third-party dependencies.

From this directory:
```bash
python -m unittest discover -s tests -v
```

Quick example:
```python
from course_waitlist import CourseRegistrationService, Learner

service = CourseRegistrationService("CS201", 2, "CS101")
print(service.enroll(Learner("learner-1", frozenset({"CS101"}))))
```

## AI prompt and use record
This assessment was completed with AI assistance in this conversation.

**Prompt used (summary):** “Implement a bounded course enrollment, drop, and FIFO waitlist-promotion service; state prerequisite and ineligible-waitlist policy; include focused tests, design notes, setup instructions, and an honest AI-use record.”

**AI contribution:** Proposed a minimal in-memory service, a single prerequisite rule, a skip-and-retain policy for learners who become ineligible while waiting, a lock around state transitions, and tests for the acceptance criteria.

**Review decisions:** The service boundary and policy were accepted. The implementation was reviewed against the acceptance criteria; validation, duplicate handling, invariant checks, and a concurrency test were included. The ineligible-at-promotion test intentionally simulates an upstream eligibility change by inserting a now-ineligible queue entry, because the in-memory `Learner` object itself is immutable.

**Verification evidence:** The automated test suite was run with the command above. See `TEST_RESULTS.txt`. The concurrency test launches eight simultaneous requests for the same learner and verifies exactly one enrollment and seven duplicate results.

## Limitations and follow-up risks
- In-memory state is not durable and cannot coordinate multiple application instances.
- Prerequisite eligibility is a snapshot supplied by the caller; there is no integration to a student-information system.
- Skip-and-retain can leave an ineligible learner waiting indefinitely; a production system may need an expiry, notification, or administrative removal policy.
- The queue is scanned linearly during promotion, appropriate for this small bounded slice.
- The service does not include authorization, audit history, offering lifecycle, or API transport.
