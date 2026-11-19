# AI use and verification record

## Engineering activity
AI was used to help decompose the assessment into a small service boundary, define explicit prerequisite and waitlist assumptions, draft implementation/test structure, and prepare the design and run documentation.

## Prompt record
Prompt summary: “Implement the supplied course waitlist assessment as a minimal runnable service with enrollment, dropping, FIFO promotion, prerequisite validation, duplicate protection, tests, a design specification, AI-use record, and run instructions.”

## Suggestions and decisions
| Suggestion | Decision | Review / evidence |
|---|---|---|
| Use a small in-memory service because no starter project was supplied | Accepted | Matches the assessment's stated fallback |
| Require one named prerequisite | Accepted | Explicitly documented and tested |
| Skip an ineligible queue entry but retain it in place | Accepted | Implemented consistently in promotion; tested |
| Protect transitions with a lock | Accepted | All state reads/writes use the same lock; concurrent duplicate test |
| Add a full frontend/database | Rejected | Outside the assessment scope |

## Verification
Executed `python -m unittest discover -s tests -v`. The suite covers available capacity, full capacity, duplicate requests, FIFO promotion, ineligible prerequisite rejection, invalid/repeated drops, invalid capacity, and concurrent duplicate requests.

AI-generated code was treated as a draft and reviewed against the stated invariants and acceptance criteria. No claim is made that AI independently verified correctness; the test run is the concrete verification evidence.
