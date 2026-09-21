# Общий интерфейс эксперимента

Все изменения только в тренировочном репозитории. Исполнители владеют разными
файлами. Интегратор — корневой агент. Не делать commit/push без отдельной команды.

- `rehearsal.contracts`: Draft, Fact, Chain, CheckResult, RunRecord (корневой агент).
- `rehearsal.baseline`: `async make_draft(message: str, gateway) -> Draft`.
- `rehearsal.model`: ModelGateway(model, log),
  `async generate(instructions: str, payload: dict, output_type: type[BaseModel], stage: str) -> BaseModel`,
  `async text(instructions: str, payload: dict, stage: str) -> str`.
  Gateway uses Agents SDK Agent/Runner; model is supplied explicitly by configuration.
- `rehearsal.scratch_check`: `async check(message: str, draft: Draft, gateway, log) -> CheckResult`.
- `rehearsal.framework_check`: same `check` signature.
- `log.emit(event: str, **data)` logs timestamped JSONL; `log.directory` is pathlib.Path
  for run-specific artifacts. Log implementation and CLI belong to integrator.

The baseline runs ONCE per message. Both checkers receive the same draft. A
checker must not mutate that baseline. No runtime mock fallback. Tests may inject
scripted model outputs, labelled simulation. No live API calls by subagents.
Never log credentials, headers, .env content or hidden reasoning. Log explicit
inputs, structured outputs, concise justification, tool observations, versions,
usage and timings. Errors may include secret values; redact before writing.

No fixed default model name: OPENAI_MODEL is required for live calls.
Category convention for the prototype: справка = informational question (including
document requests); жалоба = reported dissatisfaction or malfunction; другое =
remaining intentions/actions, including consultation booking. This is an explicit
interpretation of an ambiguous task category, not an organizer-provided gold label.

Missing information alone is not a contradiction. Do not force a contradiction or
leap if none is found. All stages must be considered, absent findings can be null
or empty with a summary. Technical failure is inconclusive/error, not a user
contradiction. A proposed leap requires separate reassessment before 'resolved'.
Unresolved contradiction -> specific clarification question. Preserve one category
and one final draft per message. A question can be the final draft.

Checker semantics remain provisional until user provides/accepts a worked chain.
