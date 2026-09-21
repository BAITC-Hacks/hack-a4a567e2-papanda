# Baseline development log

All timestamps UTC, 2026-09-21. Agent: baseline. Training repository only.

- Before 14:16: read local AGENTS.md, TASK.md, docs/INTERFACE.md and contracts.py.
- Before 14:16: applied OpenAI Docs skill; searched official Agents SDK custom
  model/provider documentation, opened SDK overview, quickstart and
  [Models and providers](https://developers.openai.com/api/docs/guides/agents/models).
  Official guide directs non-OpenAI models to SDK provider adapters.
- Before 14:16: implemented shared baseline with informational/complaint/other
  categories per interface contract. No dialectical logic added.
- Before 14:16: implemented explicit Agents SDK model adapter, client timeout,
  bounded retries, disabled remote tracing, validated structured output, local
  request/output/usage/error-type events. No provider exception text logged.
- Before 14:16: added native structured output and explicit json_prompt mode for
  compatible endpoints without native schema support. The latter still validates
  JSON locally and fails on malformed output; no fallback synthetic answer.
- 14:16: first offline pytest attempt failed: pytest not installed in new .venv
  yet. Installation owned by root agent. No model API call made.
- 14:17: dependency installation completed by root; confirmed installed adapter
  constructor signatures and RunConfig.tracing_disabled field. Seven offline
  tests passed, including real SDK Agent construction with mocked Runner.
- 14:18: moved usage event before local validation so invalid outputs retain
  token accounting; added safe HTTP status code to error events at integration
  review request. Seven offline tests passed again (1.41 seconds).

Offline tests simulate Runner outputs; they verify plumbing and failure behavior,
not Russian answer quality or actual provider compatibility. No secrets read.

- 14:22: inspected root's live results in
  `runs/20260921T142129Z-20e2c3d7/results.json` (left untouched). Groq's configured
  model invented certificate documents/procedure, assumed a medical consultation,
  and asserted parking by the main entrance. Schema success did not imply factual
  quality. Tightened baseline instructions: incoming message is the only factual
  source; no typical procedures or inferred institution details; missing facts
  produce a specific clarification; ambiguous consultation remains unspecified.
  This is generic baseline grounding, not a dialectical checker or hardcoded
  replies to the supplied messages. Root owns subsequent live verification.
