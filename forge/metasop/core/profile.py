from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional

if TYPE_CHECKING:  # pragma: no cover
    from forge.metasop.models import Artifact, SopStep
    from forge.metasop.orchestrator import MetaSOPOrchestrator


class ProfileManager:
    """Manages role profiles and capability checks for MetaSOP runs."""

    def __init__(self, orchestrator: "MetaSOPOrchestrator") -> None:
        self._orch: Any = orchestrator

    # ------------------------------------------------------------------
    # Profile retrieval helpers
    # ------------------------------------------------------------------
    def get_profiles(self) -> Dict[str, Any]:
        """Return the orchestrator's profiles mapping, defaulting to empty dict."""
        profiles = getattr(self._orch, "profiles", None)
        return profiles if isinstance(profiles, dict) else {}

    def get_role_profile(self, role: str) -> Any | None:
        """Return the role profile for the given role if available."""
        return self.get_profiles().get(role)

    def resolve_role_profile(self, step: "SopStep") -> Any | None:
        """Fetch the profile for a step and emit a skipped event if missing."""
        profile = self.get_role_profile(step.role)
        if profile is not None:
            return profile

        self._emit_missing_profile_event(step)
        return None

    def list_roles(self) -> List[str]:
        """List all known roles from the loaded profiles."""
        return list(self.get_profiles().keys())

    # ------------------------------------------------------------------
    # Capability matrix enforcement
    # ------------------------------------------------------------------
    def check_capability_matrix(
        self, step: "SopStep", done: Dict[str, "Artifact"] | None = None
    ) -> bool:
        """Validate that the step's role satisfies required capabilities."""
        if not getattr(self._orch.settings, "enforce_capability_matrix", False):
            return True

        req_caps = self._get_required_capabilities(step)
        if not req_caps:
            return True

        role_caps = self.get_role_capabilities(step.role)
        return self._validate_capabilities(step, req_caps, role_caps)

    def get_role_capabilities(self, role: str) -> List[str]:
        """Return capability list for the specified role."""
        profile = self.get_role_profile(role)
        try:
            capabilities = (
                profile.capabilities
                if profile and hasattr(profile, "capabilities")
                else []
            )
            return list(capabilities) if isinstance(capabilities, Iterable) else []
        except (AttributeError, TypeError):
            return []

    def list_all_capabilities(self) -> List[str]:
        """Aggregate capabilities advertised by all profiles."""
        all_caps = set()
        for profile in self.get_profiles().values():
            caps = getattr(profile, "capabilities", None) or []
            try:
                for capability in caps:
                    all_caps.add(capability)
            except TypeError:
                continue
        return sorted(all_caps)

    def _get_required_capabilities(self, step: "SopStep") -> Optional[List[str]]:
        req_caps = getattr(step, "required_capabilities", None)
        if not req_caps:
            extras = getattr(step, "extras", None)
            if extras and hasattr(extras, "get"):
                req_caps = extras.get("required_capabilities")
        return req_caps

    def _validate_capabilities(
        self, step: "SopStep", req_caps: Iterable[str], role_caps: Iterable[str]
    ) -> bool:
        if not isinstance(req_caps, (list, tuple, set)):
            return True

        role_caps_set = set(role_caps)
        self._emit_capability_advisories(step, req_caps, role_caps_set)

        missing = [cap for cap in req_caps if cap not in role_caps_set]
        if missing:
            self._orch._emit_event(
                {
                    "step_id": step.id,
                    "role": step.role,
                    "status": "skipped",
                    "reason": "capabilities_missing",
                    "meta": {"required": list(req_caps), "missing": missing},
                },
            )
            return False

        return True

    def _emit_capability_advisories(
        self, step: "SopStep", req_caps: Iterable[str], known_caps: Iterable[str]
    ) -> None:
        try:
            known = set(known_caps)
            if not known:
                known.update(self.list_all_capabilities())

            unknown = [cap for cap in req_caps if cap not in known]
            if unknown:
                self._orch._emit_event(
                    {
                        "step_id": step.id,
                        "role": step.role,
                        "status": "advisory",
                        "reason": "unknown_capabilities",
                        "meta": {"unknown": unknown},
                    },
                )
        except Exception:  # pragma: no cover - defensive guard
            pass

    # ------------------------------------------------------------------
    # Event helpers
    # ------------------------------------------------------------------
    def _emit_missing_profile_event(self, step: "SopStep") -> None:
        self._orch._emit_event(
            {
                "step_id": step.id,
                "role": step.role,
                "status": "skipped",
                "reason": "no_role_profile",
            }
        )


__all__ = ["ProfileManager"]
