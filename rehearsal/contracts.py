"""Shared, inspectable outputs; schema validation is not semantic proof."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Draft(StrictModel):
    category: Literal["справка", "жалоба", "другое"]
    reply: str = Field(min_length=1)


class Fact(StrictModel):
    statement: str
    basis: Literal["message", "draft", "inference", "assumption"]


class Chain(StrictModel):
    simplest: str
    development: list[Fact]
    opposites: list[str]
    contradiction: str | None
    leap: str | None


class CheckResult(StrictModel):
    status: Literal["clear", "resolved", "needs_clarification", "inconclusive"]
    draft: Draft
    chain: Chain
    plan: list[str]
    clarification: str | None
    summary: str


class RunRecord(StrictModel):
    message_id: int
    message: str
    baseline: Draft | None
    checks: dict[str, CheckResult]
    errors: dict[str, str]
