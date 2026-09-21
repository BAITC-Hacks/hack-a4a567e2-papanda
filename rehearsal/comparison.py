"""Run independent checker experiments against the same baseline.

This orchestrates checkers supplied by the caller; it implements no dialectical
interpretation and never fabricates a checker result.
"""
from collections.abc import Awaitable, Callable
from time import perf_counter

from rehearsal.contracts import CheckResult, Draft


Checker = Callable[[str, Draft, object, object], Awaitable[CheckResult]]


class InvalidCheckResult(ValueError):
    """The supplied result contradicts its declared output contract."""


def validate_result(result: CheckResult) -> None:
    """Check structural consistency, not philosophical or factual correctness.

    A clarification is the final reply verbatim (ignoring boundary whitespace),
    so callers do not need semantic guessing to identify the user-visible action.
    A resolved result still requires a separate substantive reassessment by its
    checker; the presence of a plan and leap cannot prove their success.
    """
    if not isinstance(result, CheckResult):
        raise InvalidCheckResult("Expected CheckResult")
    if result.status == "needs_clarification":
        if not result.clarification or not result.clarification.strip():
            raise InvalidCheckResult("Clarification question is required")
        if result.draft.reply.strip() != result.clarification.strip():
            raise InvalidCheckResult("Final reply must be the clarification")
    if result.status == "resolved":
        if not result.chain.contradiction or not result.chain.contradiction.strip():
            raise InvalidCheckResult("Resolved requires a contradiction")
        if not result.chain.leap or not result.chain.leap.strip():
            raise InvalidCheckResult("Resolved requires a leap")
        if not result.plan or any(not step.strip() for step in result.plan):
            raise InvalidCheckResult("Resolved requires a nonempty plan")
    if result.status == "clear" and result.chain.contradiction is not None:
        raise InvalidCheckResult("Clear cannot assert a contradiction")


async def compare(
    message: str,
    draft: Draft,
    checkers: dict[str, Checker],
    gateway,
    log,
) -> tuple[dict[str, CheckResult], dict[str, str]]:
    """Execute sequentially to avoid making service quotas affect comparisons.

    Each checker receives an isolated deep copy. Exceptions are represented only
    by their class names: exception messages may contain credentials or URLs.
    Inconclusive is preserved as a result and explicitly never logged as passed.
    Cancellation and other BaseException subclasses propagate to the caller.
    """
    results: dict[str, CheckResult] = {}
    errors: dict[str, str] = {}
    for name, checker in checkers.items():
        started = perf_counter()
        log.emit("checker_started", checker=name)
        try:
            result = await checker(message, draft.model_copy(deep=True), gateway, log)
            validate_result(result)
            # Detach returned objects as well as supplied inputs.
            results[name] = result.model_copy(deep=True)
        except Exception as exc:
            errors[name] = type(exc).__name__
            log.emit(
                "checker_failed", checker=name, error_type=errors[name],
                elapsed_seconds=perf_counter() - started,
            )
        else:
            log.emit(
                "checker_finished", checker=name, status=result.status,
                passed=result.status in {"clear", "resolved"},
                elapsed_seconds=perf_counter() - started,
            )
    return results, errors
