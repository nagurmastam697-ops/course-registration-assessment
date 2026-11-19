import threading
import unittest
from course_waitlist import CourseRegistrationService, Learner


def learner(name, *completed):
    return Learner(name, frozenset(completed))


class CourseRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.service = CourseRegistrationService("CS201", 2, "CS101")

    def test_enroll_with_available_capacity(self):
        self.assertEqual(self.service.enroll(learner("A", "CS101")).status, "enrolled")
        self.assertEqual(self.service.snapshot()["open_seats"], 1)

    def test_full_course_adds_eligible_learner_to_waitlist(self):
        self.service.enroll(learner("A", "CS101"))
        self.service.enroll(learner("B", "CS101"))
        self.assertEqual(self.service.enroll(learner("C", "CS101")).status, "waitlisted")
        self.assertEqual(self.service.snapshot()["waitlist"], ("C",))

    def test_duplicate_enrollment_does_not_duplicate_waitlist(self):
        for name in ("A", "B"):
            self.service.enroll(learner(name, "CS101"))
        self.service.enroll(learner("C", "CS101"))
        self.assertEqual(self.service.enroll(learner("C", "CS101")).status, "duplicate")
        self.assertEqual(self.service.snapshot()["waitlist"], ("C",))

    def test_drop_promotes_fifo_eligible_learner(self):
        for name in ("A", "B", "C", "D"):
            self.service.enroll(learner(name, "CS101"))
        result = self.service.drop("A")
        self.assertEqual(result.promoted_learner_id, "C")
        self.assertEqual(self.service.snapshot()["enrolled"], ("B", "C"))
        self.assertEqual(self.service.snapshot()["waitlist"], ("D",))

    def test_ineligible_front_is_skipped_but_retained(self):
        self.service.enroll(learner("A", "CS101"))
        self.service.enroll(learner("B", "CS101"))
        # Simulate prerequisite eligibility changing in the upstream system.
        self.service._waitlist.append(learner("X", "OTHER"))
        self.service._waitlist.append(learner("C", "CS101"))
        result = self.service.drop("A")
        self.assertEqual(result.promoted_learner_id, "C")
        self.assertEqual(self.service.snapshot()["waitlist"], ("X",))

    def test_prerequisite_failure_never_enrolls_or_waitlists(self):
        result = self.service.enroll(learner("A", "OTHER"))
        self.assertEqual(result.status, "ineligible")
        self.assertEqual(self.service.snapshot()["enrolled"], ())
        self.assertEqual(self.service.snapshot()["waitlist"], ())

    def test_invalid_and_repeated_drop_are_safe(self):
        self.assertEqual(self.service.drop("").status, "invalid")
        self.assertEqual(self.service.drop("missing").status, "not_enrolled")
        self.service.enroll(learner("A", "CS101"))
        self.assertEqual(self.service.drop("A").status, "dropped")
        self.assertEqual(self.service.drop("A").status, "not_enrolled")
        self.assertEqual(self.service.snapshot()["open_seats"], 2)

    def test_invalid_capacity_rejected(self):
        with self.assertRaises(ValueError):
            CourseRegistrationService("CS201", 0, "CS101")

    def test_concurrent_duplicate_requests_are_serialized(self):
        service = CourseRegistrationService("CS201", 1, "CS101")
        barrier = threading.Barrier(8)
        results = []

        def submit():
            barrier.wait()
            results.append(service.enroll(learner("same", "CS101")).status)

        threads = [threading.Thread(target=submit) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(results.count("enrolled"), 1)
        self.assertEqual(results.count("duplicate"), 7)
        self.assertEqual(service.snapshot()["enrolled"], ("same",))


if __name__ == "__main__":
    unittest.main()
