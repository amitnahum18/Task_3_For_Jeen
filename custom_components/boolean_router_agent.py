"""Orchestrator Agent variant that routes its input through one of two boolean outputs.

Subclasses the built-in Agent component (lfx.components.models_and_agents.agent.
AgentComponent) so it keeps every existing capability (model selection, memory,
tools, system prompt) unchanged, and adds a True/False branch pair modeled on the
built-in If-Else component's stop()/group_outputs pattern: exactly one branch emits
the input text downstream, the other is stopped so nothing runs on that edge.

The True/False decision itself is fully driven by the "Agent Instructions" system
prompt already present on the base Agent component — this component does not
hardcode what True/False means. Write the routing rule directly in Agent
Instructions, e.g.:

    Decide whether this request needs a database lookup.
    Return True if it does, False if it is a greeting or needs no data.

The decision is obtained through the base class's existing structured-output path
(json_response(), same mechanism the "Output Schema" table already exposes in the
UI) with a single forced boolean field, so no tool-calling agent loop runs just to
extract True/False when the model supports native structured output.
"""

import copy

from lfx.components.models_and_agents.agent import AgentComponent
from lfx.io import Output
from lfx.log.logger import logger
from lfx.schema.message import Message
from lfx.schema.table import EditMode

# Forced off by default (see BooleanRouterAgentComponent.inputs below): the base
# Agent enables both by default, which makes get_agent_requirements() populate
# self.tools even when nothing is wired to the Tools input. json_response() then
# sees has_tools=True and forces the slow prompt-fallback structured-output path
# instead of the native one — and the fallback's free-text answer often isn't
# strict JSON, which surfaced as every decision silently defaulting to False.
_TOOL_DEFAULTS_OFF = {"add_current_date_tool": False, "add_calculator_tool": False}

_DECISION_FIELD = "decision"
_DECISION_SCHEMA = [
    {
        "name": _DECISION_FIELD,
        "display_name": "Decision",
        "type": "bool",
        "description": (
            "True or False, decided strictly according to the routing rule described "
            "in Agent Instructions. Return only this field."
        ),
        "default": "field",
        "multiple": "False",
        "edit_mode": EditMode.INLINE,
    }
]


def _inputs_with_tools_off():
    """Copy AgentComponent.inputs with the two default-on tool toggles defaulted to False."""
    result = []
    for inp in AgentComponent.inputs:
        if inp.name in _TOOL_DEFAULTS_OFF:
            inp = copy.deepcopy(inp)
            inp.value = _TOOL_DEFAULTS_OFF[inp.name]
        result.append(inp)
    return result


def _extract_text(value) -> str:
    if isinstance(value, str):
        return value
    text = getattr(value, "text", None)
    if isinstance(text, str):
        return text
    return str(value) if value is not None else ""


class BooleanRouterAgentComponent(AgentComponent):
    display_name = "Orchestrator Agent (True/False Router)"
    description = (
        "Runs the Agent, asks it for a single True/False decision (per Agent "
        "Instructions), and forwards the input text through exactly one of two "
        "outputs — the other branch is stopped, just like the If-Else component."
    )
    name = "BooleanRouterAgent"
    icon = "split"

    inputs = _inputs_with_tools_off()

    outputs = [
        Output(display_name="True", name="true_result", method="true_response", group_outputs=True),
        Output(display_name="False", name="false_result", method="false_response", group_outputs=True),
    ]

    def _pre_run_setup(self):
        if hasattr(super(), "_pre_run_setup"):
            super()._pre_run_setup()
        # Cleared per run so a re-used component instance (e.g. across Playground
        # turns) never leaks a stale decision from a previous message.
        if hasattr(self, "_cached_decision"):
            del self._cached_decision

    async def _decide(self) -> bool:
        """Return the agent's True/False decision, computed at most once per run.

        Both true_response() and false_response() call this — caching on the
        instance (reset in _pre_run_setup) avoids running the LLM twice for what
        must be a single, consistent routing decision.
        """
        if hasattr(self, "_cached_decision"):
            return self._cached_decision

        self.output_schema = _DECISION_SCHEMA
        data = await self.json_response()
        payload = getattr(data, "data", None) or {}

        error = payload.get("error") if isinstance(payload, dict) else None
        if error:
            # Fail safe toward False rather than raising, so a routing failure
            # degrades to "no route taken" instead of crashing the flow.
            await logger.aerror(f"BooleanRouterAgent decision failed, defaulting to False: {error}")
            decision = False
        else:
            raw = payload.get(_DECISION_FIELD) if isinstance(payload, dict) else None
            if isinstance(raw, bool):
                decision = raw
            elif isinstance(raw, str):
                decision = raw.strip().lower() in {"true", "1", "yes"}
            else:
                decision = bool(raw)

        self._cached_decision = decision
        return decision

    def _stop_branch(self, output_name: str) -> None:
        """Stop a branch AND mark it conditionally excluded.

        stop() alone only flags the edge INACTIVE for this run; it does not tell
        the graph engine that the branch's entire downstream subgraph (e.g. the
        Analysis Agent behind "true_result") never ran. Without the exclusion
        call, a node fed by both branches (like a merge node collecting True and
        False into one input) tries to build the stopped branch anyway and fails
        with "Component ... has not been built yet".
        """
        self.stop(output_name)
        self.graph.exclude_branch_conditionally(self._id, output_name=output_name)

    async def true_response(self) -> Message:
        decision = await self._decide()
        message = Message(text=_extract_text(self.input_value))
        if decision:
            self.status = message
            return message
        self._stop_branch("true_result")
        return Message(text="")

    async def false_response(self) -> Message:
        decision = await self._decide()
        message = Message(text=_extract_text(self.input_value))
        if not decision:
            self.status = message
            return message
        self._stop_branch("false_result")
        return Message(text="")
