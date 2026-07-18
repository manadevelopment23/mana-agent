"""Model-driven entry routing and dynamic route availability for chat turns."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Literal

from langchain_core.messages import HumanMessage, SystemMessage


EntryRouteName = Literal[
    "conversation",
    "coding",
    "gmail",
    "calendar",
    "search",
    "repository",
    "automation",
    "unsupported",
]


@dataclass(frozen=True, slots=True)
class RouteAvailability:
    available: bool
    configured: bool = True
    authorized: bool = True
    reason: str = ""
    setup_action: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RouteRegistration:
    name: EntryRouteName
    description: str
    availability: Callable[[], RouteAvailability]
    tools: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EntryRouteContext:
    session_id: str
    conversation_id: str
    turn_id: str
    previous_route: str = ""
    conversation_summary: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EntryRoutingDecision:
    route: EntryRouteName
    confidence: float
    reason: str
    reuse_active_route: bool = False
    source: str = "model"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EntryRoutingError(RuntimeError):
    """The model did not return a valid entry-routing decision."""


class EntryRouteRegistry:
    """Registry of execution routes and their live runtime availability."""

    def __init__(self) -> None:
        self._routes: dict[str, RouteRegistration] = {}

    def register(self, registration: RouteRegistration) -> None:
        name = str(registration.name).strip()
        if not name:
            raise ValueError("entry route name is required")
        self._routes[name] = registration

    def get(self, name: str) -> RouteRegistration:
        try:
            return self._routes[str(name)]
        except KeyError as exc:
            raise EntryRoutingError(f"Unknown entry route: {name or '<missing>'}") from exc

    def snapshot(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for name in sorted(self._routes):
            registration = self._routes[name]
            availability = registration.availability()
            rows.append(
                {
                    "name": registration.name,
                    "description": registration.description,
                    "tools": list(registration.tools),
                    "availability": availability.to_dict(),
                }
            )
        return rows

    @property
    def names(self) -> set[str]:
        return set(self._routes)


ENTRY_ROUTER_PROMPT = """You are Mana-Agent's first-turn entry router.
Select exactly one registered execution route before any conversational response is generated.
Routing is independent from response generation: return a decision only and never answer the user.

Use the supplied live route registry. A route may be selected when unavailable so its executor can
return the registry's truthful setup or authorization error; do not send a supported connector
request to conversation merely because its connector is unavailable.

Route semantics:
- conversation: ordinary discussion that needs no tool, connector, repository, or coding action.
- coding: repository code/file changes handled by the Codex coding workflow.
- gmail: inspect or act on the user's Gmail/email account through registered email tools.
- calendar: calendar account operations through a registered calendar connector.
- search: current or external public information retrieval.
- repository: read-only local repository questions or inspection.
- automation: create, inspect, or manage an automation.
- unsupported: no registered route can represent the request safely.

Current mailbox/account data is never ordinary conversation. Requests to check an inbox, latest
email, Gmail message, email thread, or mailbox must select gmail when that registered route
represents the request. The conversation route must never speculate about connector availability.

Use previous_route and conversation_summary only for continuity. Reuse the active route for a true
follow-up; reroute when the user's intent changes. Do not route by isolated keywords alone.

Return JSON only:
{
  "route": "conversation|coding|gmail|calendar|search|repository|automation|unsupported",
  "confidence": 0.0,
  "reason": "short routing reason",
  "reuse_active_route": false
}
"""


class EntryRouter:
    """Obtain and validate the single entry decision for one gateway turn."""

    def __init__(self, *, llm: Any, registry: EntryRouteRegistry) -> None:
        self.llm = llm
        self.registry = registry

    def route(
        self,
        *,
        user_prompt: str,
        context: EntryRouteContext,
    ) -> EntryRoutingDecision:
        if self.llm is None or not callable(getattr(self.llm, "invoke", None)):
            raise EntryRoutingError(
                "Model decision failed: entry_route. No response was generated. "
                "Reason: routing model is unavailable."
            )
        payload = {
            "user_prompt": str(user_prompt or "").strip(),
            "context": context.to_dict(),
            "routes": self.registry.snapshot(),
        }
        try:
            response = self.llm.invoke(
                [
                    SystemMessage(content=ENTRY_ROUTER_PROMPT),
                    HumanMessage(content=json.dumps(payload, ensure_ascii=False, sort_keys=True)),
                ]
            )
            content = getattr(response, "content", response)
            if isinstance(content, list):
                content = " ".join(
                    str(part.get("text", part)) if isinstance(part, dict) else str(part)
                    for part in content
                )
            return self._validate(_extract_json(str(content)))
        except EntryRoutingError:
            raise
        except Exception as exc:
            raise EntryRoutingError(
                "Model decision failed: entry_route. No response was generated. "
                f"Reason: {exc}"
            ) from exc

    def _validate(self, payload: dict[str, Any]) -> EntryRoutingDecision:
        route = str(payload.get("route") or "").strip()
        if route not in self.registry.names:
            raise EntryRoutingError(
                "Model decision failed: entry_route. No response was generated. "
                f"Reason: unknown route {route or '<missing>'}."
            )
        try:
            confidence = float(payload.get("confidence"))
        except (TypeError, ValueError) as exc:
            raise EntryRoutingError(
                "Model decision failed: entry_route. No response was generated. "
                "Reason: confidence must be numeric."
            ) from exc
        if not 0.0 <= confidence <= 1.0:
            raise EntryRoutingError(
                "Model decision failed: entry_route. No response was generated. "
                "Reason: confidence must be between 0 and 1."
            )
        reason = str(payload.get("reason") or "").strip()
        if not reason:
            raise EntryRoutingError(
                "Model decision failed: entry_route. No response was generated. "
                "Reason: routing reason is required."
            )
        return EntryRoutingDecision(
            route=route,  # type: ignore[arg-type]
            confidence=confidence,
            reason=reason,
            reuse_active_route=bool(payload.get("reuse_active_route", False)),
        )


def _extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.removeprefix("```json").removeprefix("```").strip()
        stripped = stripped.removesuffix("```").strip()
    start, end = stripped.find("{"), stripped.rfind("}")
    if start >= 0 and end >= start:
        stripped = stripped[start : end + 1]
    payload = json.loads(stripped)
    if not isinstance(payload, dict):
        raise ValueError("router output must be a JSON object")
    return payload


def gmail_route_availability() -> RouteAvailability:
    """Inspect local Gmail registration and credential presence without contacting Gmail."""
    from mana_agent.connectors.email.auth.credential_store import CredentialStore
    from mana_agent.connectors.email.config import load_accounts
    from mana_agent.connectors.email.exceptions import EmailConnectorError
    from mana_agent.connectors.email.models import EmailPermission

    accounts = [
        account
        for account in load_accounts()
        if account.enabled and account.provider == "gmail"
    ]
    if not accounts:
        return RouteAvailability(
            available=False,
            configured=False,
            authorized=False,
            reason="No enabled Gmail account is configured.",
            setup_action=(
                "Run `mana-agent connector email add --provider gmail "
                "--client-secret-file <google-client.json> --permissions email.read`."
            ),
        )
    readable = [account for account in accounts if EmailPermission.READ in account.granted_permissions]
    if not readable:
        return RouteAvailability(
            available=False,
            configured=True,
            authorized=False,
            reason="The configured Gmail account has not granted email.read permission.",
            setup_action=(
                f"Run `mana-agent connector email reconnect {accounts[0].id} "
                "--client-secret-file <google-client.json> --permissions email.read`."
            ),
            details={"account_id": accounts[0].id, "provider": "gmail"},
        )
    account = readable[0]
    if not account.secret_ref:
        return RouteAvailability(
            available=False,
            configured=True,
            authorized=False,
            reason="The Gmail credential reference is missing.",
            setup_action=f"Reconnect Gmail account `{account.id}`.",
            details={"account_id": account.id, "provider": "gmail"},
        )
    try:
        CredentialStore().get(account.secret_ref)
    except EmailConnectorError as exc:
        return RouteAvailability(
            available=False,
            configured=True,
            authorized=False,
            reason=str(exc),
            setup_action=f"Reconnect Gmail account `{account.id}`.",
            details={
                "account_id": account.id,
                "provider": "gmail",
                "provider_error": exc.to_payload(),
            },
        )
    return RouteAvailability(
        available=True,
        configured=True,
        authorized=True,
        details={"account_id": account.id, "provider": "gmail"},
    )
