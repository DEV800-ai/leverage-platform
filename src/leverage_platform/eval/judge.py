"""LLM-as-judge evaluation primitive.

The judge is itself an `@agent` — every judge call produces its own AgentRun
row. Products use the judge AFTER `rule_eval` has passed structural checks;
the judge handles subjective fit questions.

Phase 3: minimum-viable. Phase 4 will add per-criterion confidence scoring
and parallel-judge ensembles.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from pydantic import BaseModel

from leverage_platform.llm import LLMParameters
from leverage_platform.runtime import AgentContext, agent
from leverage_platform.schemas import EvalReport

if TYPE_CHECKING:
    pass

JUDGE_PROMPT_TEMPLATE = """\
You are evaluating an artifact against a rubric of subjective questions.

Artifact (JSON):
{artifact_json}

Rubric questions (each is judged independently):
{rubric_questions}

For each rubric question, decide whether the artifact satisfies it. Be honest;
do not pass weak artifacts. Return an EvalReport with:
- criteria: one EvalCriterion per rubric question — name (the question itself),
  passed (true/false), reason (one sentence)
- accepted: true iff every criterion passes
- summary: a short overall summary (one sentence)
"""


@agent(name="llm_judge", schema=EvalReport, prompt_name="llm_judge.v1")
async def llm_judge(
    ctx: AgentContext,
    *,
    artifact: BaseModel,
    rubric: list[str],
    model: str | None = None,
) -> EvalReport:
    """Judge an artifact against a rubric. One LLM call, one AgentRun row.

    Returns an EvalReport. The criteria list mirrors the rubric questions.
    """
    artifact_json = artifact.model_dump(mode="json")
    rubric_questions = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(rubric))

    result = await ctx.invoke_llm(
        template=JUDGE_PROMPT_TEMPLATE,
        variables={
            "artifact_json": json.dumps(artifact_json, sort_keys=True),
            "rubric_questions": rubric_questions,
        },
        schema=EvalReport,
        prompt_name="llm_judge.v1",
        model=model,
        parameters=LLMParameters(temperature=0.0),
    )
    return result.value
