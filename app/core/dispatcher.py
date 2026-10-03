"""Project H Central Action Dispatcher (PH-040).

The ActionDispatcher guarantees the central security invariant:
NO executor receives an action before:
schema validation -> trusted materialization -> policy evaluation ->
approval-floor merge -> executor-specific validation -> execution constraints.

Provides clearly separated pathways for:
- External model/agent ActionRequest proposals
- Deterministic RegistryMatch resolution
"""

import collections
from collections.abc import Callable
from pathlib import Path
import time
from typing import Any, Mapping

from app.actions.matcher import substitute_arguments
from app.actions.registry import ActionRegistry, RegistryMatch
from app.actions.schema import ActionDefinition, ActionRequest, ActionResult
from app.browser.protocol import BrowserBridge
from app.executors.files import FileExecutor
from app.executors.process import ProcessExecutor
from app.executors.xdg import XdgExecutor
from app.policy.engine import PolicyDecision, PolicyEngine, PolicyEvaluation
from app.policy.risk import RiskLevel

MAX_COMPOSITE_DEPTH = 5
MAX_COMPOSITE_STEPS = 32
MAX_COMPOSITE_TOTAL_STEPS = 64

AuditEvent = dict[str, Any]
AuditSink = Callable[[AuditEvent], None]


class _CompositeBudget:
    """Tracks global step execution budget across nested composites."""

    def __init__(self, max_steps: int = MAX_COMPOSITE_TOTAL_STEPS) -> None:
        self.max_steps = max_steps
        self.executed_steps = 0


class ActionDispatcher:
    """Central secure action dispatcher."""

    def __init__(
        self,
        policy_engine: PolicyEngine,
        registry: ActionRegistry,
        process_executor: ProcessExecutor | None = None,
        file_executor: FileExecutor | None = None,
        xdg_executor: XdgExecutor | None = None,
        browser_bridge: BrowserBridge | None = None,
        audit_sink: AuditSink | None = None,
    ) -> None:
        self.policy_engine = policy_engine
        self.registry = registry
        self.process_executor = process_executor
        self.file_executor = file_executor
        self.xdg_executor = xdg_executor
        self.browser_bridge = browser_bridge
        self.audit_sink = audit_sink
        self._recent_audits: collections.deque[AuditEvent] = collections.deque(maxlen=256)

    @property
    def recent_audits(self) -> tuple[AuditEvent, ...]:
        """Expose an immutable tuple of dict copies of recent audit events."""
        return tuple(dict(event) for event in self._recent_audits)

    def _sanitize_error_code(self, error: str | None) -> str:
        """Map raw error string to sanitized error_code string for audit logging."""
        if not error:
            return "NONE"
        err_upper = error.upper()
        if "DENIED BY POLICY" in err_upper or "FORBIDDEN" in err_upper:
            return "POLICY_DENIED"
        elif "REQUIRES USER APPROVAL" in err_upper or "APPROVAL BROKER" in err_upper:
            return "APPROVAL_REQUIRED"
        elif "STALE REGISTRYMATCH" in err_upper:
            return "STALE_MATCH"
        elif "NOT FOUND OR DISABLED" in err_upper or "IS DISABLED" in err_upper:
            return "DISABLED_ACTION"
        elif "INVALID COMPOSITE" in err_upper:
            return "INVALID_COMPOSITE"
        elif "RECURSION DEPTH" in err_upper:
            return "RECURSION_LIMIT_EXCEEDED"
        elif "STEP COUNT LIMIT" in err_upper:
            return "STEP_BUDGET_EXCEEDED"
        elif "ARGUMENT SUBSTITUTION" in err_upper:
            return "SUBSTITUTION_FAILED"
        elif "UNSUPPORTED EXECUTOR" in err_upper:
            return "UNSUPPORTED_EXECUTOR"
        elif "NOT CONFIGURED" in err_upper or "UNAVAILABLE" in err_upper:
            return "EXECUTOR_NOT_CONFIGURED"
        else:
            return "EXECUTOR_FAILED"

    def _emit_audit(
        self,
        request: ActionRequest,
        decision: PolicyDecision,
        success: bool,
        error: str | None,
        duration: float,
    ) -> None:
        """Emit lightweight audit metadata into internal deque and external sink if configured."""
        target = ""
        if request.tool == "process.run":
            argv = request.arguments.get("argv", [])
            target = argv[0] if argv else ""
        elif request.tool.startswith("file."):
            target = str(request.arguments.get("path", ""))
        elif request.tool == "app.open":
            target = str(request.arguments.get("target", ""))
        elif request.tool.startswith("browser."):
            target = str(request.arguments.get("url", ""))

        error_code = self._sanitize_error_code(error)

        event: AuditEvent = {
            "timestamp": time.time(),
            "request_id": request.request_id or request.id,
            "actor": request.agent_id or "user",
            "tool": request.tool,
            "policy_decision": decision.value,
            "target": target,
            "result_code": 0 if success else 1,
            "duration": round(duration, 6),
            "error_code": error_code,
            "error": error_code if not success else None,
        }

        # Always append to bounded internal audit deque
        self._recent_audits.append(event)

        if self.audit_sink is not None:
            try:
                self.audit_sink(event)
            except Exception:
                # Audit sink failure must not crash execution
                pass

    def _definition_container_gate(self, defn: ActionDefinition) -> ActionResult | None:
        """Verify definition container approval and risk floors before composite expansion."""
        if defn.approval == "deny":
            return ActionResult(success=False, error="Action denied by policy")
        if defn.approval in ("ask_user", "always_ask"):
            return ActionResult(
                success=False,
                error="Action requires user approval (approval broker not yet active in PH-040)",
            )
        try:
            def_risk = RiskLevel(defn.risk.upper())
            if def_risk in (RiskLevel.HIGH, RiskLevel.CRITICAL):
                return ActionResult(
                    success=False,
                    error="Action requires user approval (approval broker not yet active in PH-040)",
                )
        except ValueError:
            pass
        return None

    async def dispatch_request(self, request: ActionRequest) -> ActionResult:
        """
        Dispatch an ActionRequest proposed by a model, tool, or external caller.

        TRUST BOUNDARY:
        Even if request.id matches a registered action ID, it receives ZERO extra privilege.
        It is evaluated purely on its structural contents without registry definition floor.
        """
        return await self._dispatch_with_policy(request, definition=None)

    async def dispatch_match(self, match: RegistryMatch) -> ActionResult:
        """
        Dispatch a deterministic RegistryMatch from the action registry.

        TRUST BOUNDARY:
        Validates match freshness against registry.snapshot_version before materialization.
        Materializes trusted typed ActionRequest and combines policy with definition floor.
        """
        # 1. Freshness check: stale match rejected
        if match.snapshot_version != self.registry.snapshot_version:
            return ActionResult(
                success=False,
                error=f"Stale RegistryMatch rejected: match snapshot_version ({match.snapshot_version}) != active registry ({self.registry.snapshot_version})",
            )

        # 2. Fetch trusted definition
        defn = self.registry.get_definition(match.action_id)
        if defn is None or not defn.enabled:
            return ActionResult(
                success=False,
                error=f"Action '{match.action_id}' not found or disabled in active registry",
            )

        # 3. Composite action routing
        if defn.executor == "composite":
            gate_res = self._definition_container_gate(defn)
            if gate_res is not None:
                return gate_res
            budget = _CompositeBudget(MAX_COMPOSITE_TOTAL_STEPS)
            return await self._dispatch_composite(
                defn, match.captured_slots, snapshot_version=match.snapshot_version, depth=0, budget=budget
            )

        # 4. Strict slot substitution
        try:
            substituted_args = substitute_arguments(defn.arguments, match.captured_slots)
        except ValueError as exc:
            return ActionResult(success=False, error=f"Argument substitution failed: {exc}")

        # 5. Map definition executor to canonical tool
        tool = self._map_executor_to_tool(defn.executor, substituted_args)
        if tool is None:
            return ActionResult(success=False, error=f"Unsupported executor: '{defn.executor}'")

        # 6. Materialize typed ActionRequest
        request = ActionRequest(
            id=defn.id,
            tool=tool,
            arguments=substituted_args,
            risk_hint=defn.risk,
        )

        return await self._dispatch_with_policy(request, definition=defn)

    def _map_executor_to_tool(self, executor: str, arguments: dict[str, Any]) -> str | None:
        """Trusted mapping from ActionDefinition.executor to ActionRequest.tool."""
        if executor == "process":
            return "process.run"
        elif executor == "xdg_open":
            return "app.open"
        elif executor == "file":
            op = arguments.get("operation")
            if op in {"read", "write", "list", "delete"}:
                return f"file.{op}"
            return None
        elif executor == "browser":
            op = arguments.get("operation", "open")
            return f"browser.{op}"
        return None

    async def _dispatch_with_policy(
        self,
        request: ActionRequest,
        definition: ActionDefinition | None = None,
        depth: int = 0,
    ) -> ActionResult:
        """Central policy evaluation, approval-floor merge, and executor dispatch."""
        start_time = time.time()

        # 1. Evaluate against PolicyEngine
        evaluation = self.policy_engine.evaluate_detailed(request)

        # 2. Combine with ActionDefinition approval & risk floors (stricter-wins)
        if definition is not None:
            # Definition risk can only raise trusted risk, never lower it
            levels = list(RiskLevel)
            pol_idx = levels.index(evaluation.trusted_risk)
            def_idx = levels.index(RiskLevel(definition.risk.upper()))
            effective_risk = levels[max(pol_idx, def_idx)]

            # Definition approval floor
            if definition.approval == "deny":
                effective_decision = PolicyDecision.DENY
            elif definition.approval in ("ask_user", "always_ask"):
                if evaluation.decision == PolicyDecision.DENY:
                    effective_decision = PolicyDecision.DENY
                else:
                    effective_decision = PolicyDecision.ASK_USER
            elif definition.approval == "preapproved":
                # Preapproved definition does NOT grant execution on its own;
                # requires PolicyEngine to return ALLOW_PREAPPROVED
                effective_decision = evaluation.decision
            else:
                effective_decision = evaluation.decision
        else:
            effective_risk = evaluation.trusted_risk
            effective_decision = evaluation.decision

        # High or critical risk never silently executes
        if effective_risk in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            if effective_decision == PolicyDecision.ALLOW_PREAPPROVED:
                effective_decision = PolicyDecision.ASK_USER

        # 3. Handle policy decisions
        duration = time.time() - start_time
        if effective_decision == PolicyDecision.DENY:
            self._emit_audit(request, effective_decision, success=False, error="Action denied by policy", duration=duration)
            return ActionResult(success=False, error="Action denied by policy")

        if effective_decision == PolicyDecision.ASK_USER:
            # CRITICAL SECURITY INVARIANT:
            # Never execute an ASK_USER action in PH-040. An ApprovalRequest is an
            # awaiting-approval record, not an authorization grant.
            self._emit_audit(request, effective_decision, success=False, error="Action requires user approval", duration=duration)
            return ActionResult(
                success=False,
                error="Action requires user approval (approval broker not yet active in PH-040)",
            )

        # 4. Execute pre-approved action
        try:
            if request.tool == "process.run":
                if self.process_executor is None:
                    res = ActionResult(success=False, error="Process executor not configured")
                else:
                    res = await self.process_executor.execute(request, context=evaluation)

            elif request.tool.startswith("file."):
                if self.file_executor is None:
                    res = ActionResult(success=False, error="File executor not configured")
                else:
                    res = await self.file_executor.execute(request, context=evaluation)

            elif request.tool == "app.open":
                if self.xdg_executor is None:
                    res = ActionResult(success=False, error="XDG executor not configured")
                else:
                    res = await self.xdg_executor.execute(request, context=evaluation)

            elif request.tool.startswith("browser."):
                if self.browser_bridge is None:
                    res = ActionResult(
                        success=False,
                        error="Browser bridge unavailable in PH-040 (requires PH-110 native messaging bridge)",
                    )
                else:
                    res = await self.browser_bridge.execute(
                        action=request.tool.split(".", 1)[1],
                        url=str(request.arguments.get("url", "")),
                        params=request.arguments,
                    )

            else:
                res = ActionResult(success=False, error=f"Unsupported tool '{request.tool}'")

        except Exception as exc:
            res = ActionResult(success=False, error=f"Executor failed: {exc}")

        exec_duration = time.time() - start_time
        self._emit_audit(request, effective_decision, success=res.success, error=res.error, duration=exec_duration)
        return res

    async def _dispatch_composite(
        self,
        defn: ActionDefinition,
        captured_slots: Mapping[str, str],
        snapshot_version: int,
        depth: int = 0,
        budget: _CompositeBudget | None = None,
    ) -> ActionResult:
        """
        Execute a composite action sequentially through the central dispatcher.

        INVARIANTS:
        - Runtime recursion depth limit enforced.
        - Steps bound enforced.
        - Every child action passes PolicyEngine independently.
        - Parent approval NEVER authorizes a child.
        - If any child requires approval, is denied, or fails, the composite stops immediately.
        """
        if budget is None:
            budget = _CompositeBudget(MAX_COMPOSITE_TOTAL_STEPS)

        if depth > MAX_COMPOSITE_DEPTH:
            return ActionResult(
                success=False,
                error=f"Composite recursion depth ({depth}) exceeds limit ({MAX_COMPOSITE_DEPTH})",
            )

        steps = defn.arguments.get("steps")
        if not isinstance(steps, list) or not steps or len(steps) > MAX_COMPOSITE_STEPS:
            return ActionResult(success=False, error="Invalid composite steps")

        outputs = []
        for step_idx, child_id in enumerate(steps):
            budget.executed_steps += 1
            if budget.executed_steps > budget.max_steps:
                return ActionResult(
                    success=False,
                    error=f"Composite total step count limit ({budget.max_steps}) exceeded",
                )

            # Verify snapshot version before each child lookup/execution
            if self.registry.snapshot_version != snapshot_version:
                return ActionResult(
                    success=False,
                    error=f"Composite aborted: registry snapshot version changed from {snapshot_version} to active snapshot {self.registry.snapshot_version}",
                )

            # 1. Fetch current trusted child definition
            child_defn = self.registry.get_definition(child_id)
            if child_defn is None:
                return ActionResult(
                    success=False,
                    error=f"Composite step {step_idx} failed: child action '{child_id}' not found",
                )

            # 2. Re-check child enabled state at execution time
            if not child_defn.enabled:
                return ActionResult(
                    success=False,
                    error=f"Composite step {step_idx} failed: child action '{child_id}' is disabled",
                )

            # 3. If child is composite, recurse with incremented depth
            if child_defn.executor == "composite":
                gate_res = self._definition_container_gate(child_defn)
                if gate_res is not None:
                    return ActionResult(
                        success=False,
                        error=f"Composite stopped at step '{child_id}': {gate_res.error}",
                    )
                child_res = await self._dispatch_composite(
                    child_defn, captured_slots, snapshot_version=snapshot_version, depth=depth + 1, budget=budget
                )
            else:
                # 4. Strict slot substitution
                try:
                    child_args = substitute_arguments(child_defn.arguments, captured_slots)
                except ValueError as exc:
                    return ActionResult(
                        success=False,
                        error=f"Composite step {step_idx} failed argument substitution: {exc}",
                    )

                # 5. Map executor to tool
                child_tool = self._map_executor_to_tool(child_defn.executor, child_args)
                if child_tool is None:
                    return ActionResult(
                        success=False,
                        error=f"Composite step {step_idx} failed: unsupported executor '{child_defn.executor}'",
                    )

                # 6. Materialize child ActionRequest
                child_req = ActionRequest(
                    id=child_defn.id,
                    tool=child_tool,
                    arguments=child_args,
                    risk_hint=child_defn.risk,
                )

                # 7. Dispatch through central policy and executor pathway
                child_res = await self._dispatch_with_policy(child_req, definition=child_defn, depth=depth + 1)

            # 8. Stop immediately on any failure, denial, or approval required
            if not child_res.success:
                return ActionResult(
                    success=False,
                    error=f"Composite stopped at step '{child_id}': {child_res.error}",
                )

            outputs.append(f"[{child_id}]: {child_res.output}")

        return ActionResult(
            success=True,
            output="\n".join(outputs) if outputs else "Composite executed successfully",
        )
