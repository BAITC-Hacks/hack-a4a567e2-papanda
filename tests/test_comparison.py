"""Offline SIMULATION: injected checkers test orchestration, not model quality."""
import unittest

from rehearsal.comparison import compare
from rehearsal.contracts import Chain, CheckResult, Draft


class SimulationLog:
    def __init__(self):
        self.events = []

    def emit(self, event, **data):
        self.events.append((event, data))


def simulated_result(draft, status="clear", **changes):
    data = dict(
        status=status, draft=draft,
        chain=Chain(simplest="SIMULATION", development=[], opposites=[],
                    contradiction=None, leap=None),
        plan=[], clarification=None, summary="SIMULATION: no semantic claim",
    )
    data.update(changes)
    return CheckResult(**data)


class ComparisonSimulationTests(unittest.IsolatedAsyncioTestCase):
    async def test_failure_does_not_mask_other_checker_or_expose_error_text(self):
        async def failed(*args):
            raise RuntimeError("SECRET_MUST_NOT_APPEAR")

        async def successful(message, draft, gateway, log):
            return simulated_result(draft)

        log = SimulationLog()
        results, errors = await compare(
            "test", Draft(category="другое", reply="Исходный ответ"),
            {"failed": failed, "successful": successful}, None, log,
        )
        self.assertEqual(errors, {"failed": "RuntimeError"})
        self.assertEqual(list(results), ["successful"])
        self.assertNotIn("SECRET_MUST_NOT_APPEAR", repr(log.events))

    async def test_each_checker_receives_same_baseline_independently(self):
        original = Draft(category="другое", reply="Исходный ответ")
        seen = []

        async def mutate(message, draft, gateway, log):
            seen.append(draft.model_dump())
            draft.reply = "Изменённый ответ"
            return simulated_result(draft)

        async def observe(message, draft, gateway, log):
            seen.append(draft.model_dump())
            return simulated_result(draft)

        results, errors = await compare("test", original,
                                        {"first": mutate, "second": observe},
                                        None, SimulationLog())
        self.assertEqual(errors, {})
        self.assertEqual(seen, [original.model_dump(), original.model_dump()])
        self.assertEqual(original.reply, "Исходный ответ")
        self.assertEqual(results["second"].draft.reply, "Исходный ответ")

    async def test_inconsistent_contracts_are_rejected(self):
        original = Draft(category="другое", reply="Исходный ответ")
        inconsistent = [
            simulated_result(original, "resolved"),
            simulated_result(original, "needs_clarification"),
            simulated_result(original, "needs_clarification", clarification="Какой корпус?"),
            simulated_result(original, chain=Chain(
                simplest="SIMULATION", development=[], opposites=[],
                contradiction="SIMULATION", leap=None)),
        ]
        for candidate in inconsistent:
            with self.subTest(status=candidate.status):
                async def checker(*args):
                    return candidate

                results, errors = await compare("test", original, {"invalid": checker},
                                                None, SimulationLog())
                self.assertEqual(results, {})
                self.assertEqual(errors, {"invalid": "InvalidCheckResult"})

    async def test_inconclusive_is_never_reported_as_pass(self):
        async def checker(message, draft, gateway, log):
            return simulated_result(draft, "inconclusive")

        log = SimulationLog()
        results, errors = await compare(
            "test", Draft(category="другое", reply="Исходный ответ"),
            {"uncertain": checker}, None, log,
        )
        self.assertEqual(errors, {})
        self.assertEqual(results["uncertain"].status, "inconclusive")
        self.assertFalse(log.events[-1][1]["passed"])

    async def test_clarification_is_visible_in_final_reply(self):
        async def checker(message, draft, gateway, log):
            draft.reply = "Какой корпус?"
            return simulated_result(draft, "needs_clarification", clarification=draft.reply)

        results, errors = await compare(
            "test", Draft(category="другое", reply="Исходный ответ"),
            {"clarify": checker}, None, SimulationLog(),
        )
        self.assertEqual(errors, {})
        self.assertEqual(results["clarify"].draft.reply, "Какой корпус?")


if __name__ == "__main__":
    unittest.main()
