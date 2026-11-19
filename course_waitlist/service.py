"""Thread-safe, in-memory enrollment and FIFO waitlist service."""
from collections import deque
from dataclasses import dataclass
from threading import RLock


@dataclass(frozen=True)
class Learner:
    learner_id: str
    completed_prerequisites: frozenset[str]


@dataclass(frozen=True)
class Result:
    status: str
    message: str
    promoted_learner_id: str | None = None


class CourseRegistrationService:
    """
    One offering only. Ineligible waitlisted learners are skipped for the
    current promotion attempt but remain in their original FIFO position.
    """
    def __init__(self, course_id: str, capacity: int, required_prerequisite: str):
        if not isinstance(course_id, str) or not course_id.strip():
            raise ValueError("course_id must be a non-empty string")
        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity < 1:
            raise ValueError("capacity must be a positive integer")
        if not isinstance(required_prerequisite, str) or not required_prerequisite.strip():
            raise ValueError("required_prerequisite must be a non-empty string")
        self.course_id = course_id
        self.capacity = capacity
        self.required_prerequisite = required_prerequisite
        self._enrolled: dict[str, Learner] = {}
        self._waitlist: deque[Learner] = deque()
        self._lock = RLock()

    def _validate_learner(self, learner: Learner) -> str | None:
        if not isinstance(learner, Learner):
            return "learner must be a Learner"
        if not isinstance(learner.learner_id, str) or not learner.learner_id.strip():
            return "learner_id must be a non-empty string"
        if not isinstance(learner.completed_prerequisites, (set, frozenset)):
            return "completed_prerequisites must be a set of course IDs"
        if any(not isinstance(x, str) or not x.strip() for x in learner.completed_prerequisites):
            return "completed prerequisite IDs must be non-empty strings"
        return None

    def _eligible(self, learner: Learner) -> bool:
        return self.required_prerequisite in learner.completed_prerequisites

    def enroll(self, learner: Learner) -> Result:
        error = self._validate_learner(learner)
        if error:
            return Result("invalid", error)
        with self._lock:
            learner_id = learner.learner_id
            if learner_id in self._enrolled:
                return Result("duplicate", "Learner is already enrolled")
            if any(x.learner_id == learner_id for x in self._waitlist):
                return Result("duplicate", "Learner is already on the waitlist")
            if not self._eligible(learner):
                return Result("ineligible", "Required prerequisite has not been completed")
            if len(self._enrolled) < self.capacity:
                self._enrolled[learner_id] = learner
                self._assert_invariants()
                return Result("enrolled", "Enrollment confirmed")
            self._waitlist.append(learner)
            self._assert_invariants()
            return Result("waitlisted", "Course is full; learner added to waitlist")

    def drop(self, learner_id: str) -> Result:
        if not isinstance(learner_id, str) or not learner_id.strip():
            return Result("invalid", "learner_id must be a non-empty string")
        with self._lock:
            if learner_id not in self._enrolled:
                return Result("not_enrolled", "Learner is not currently enrolled")
            del self._enrolled[learner_id]
            promoted = self._promote_one()
            self._assert_invariants()
            if promoted:
                return Result(
                    "dropped_and_promoted",
                    "Enrollment dropped; waitlisted learner promoted",
                    promoted.learner_id,
                )
            return Result("dropped", "Enrollment dropped; no eligible waitlisted learner to promote")

    def _promote_one(self) -> Learner | None:
        # Scan in FIFO order. Keep ineligible entries in place; remove only
        # the earliest eligible learner that can take the open seat.
        for index, learner in enumerate(self._waitlist):
            if self._eligible(learner):
                del self._waitlist[index]
                self._enrolled[learner.learner_id] = learner
                return learner
        return None

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "course_id": self.course_id,
                "capacity": self.capacity,
                "enrolled": tuple(self._enrolled),
                "waitlist": tuple(x.learner_id for x in self._waitlist),
                "open_seats": self.capacity - len(self._enrolled),
            }

    def _assert_invariants(self) -> None:
        enrolled_ids = set(self._enrolled)
        waiting_ids = [x.learner_id for x in self._waitlist]
        assert len(self._enrolled) <= self.capacity
        assert len(waiting_ids) == len(set(waiting_ids))
        assert not (enrolled_ids & set(waiting_ids))
        assert all(self._eligible(x) for x in self._enrolled.values())
