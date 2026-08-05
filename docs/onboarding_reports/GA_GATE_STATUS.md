# Onboarding evidence status

**Interactive evidence target not met.**

The original `v1.0.0` GA gate is historical because the stable release is now published. These counts remain useful as the baseline for the next stable release; they do not describe the readiness or availability of `v1.0.0`.

Need **3× interactive pipx** + **3× interactive source** on fresh VMs (no prior `~/.grinta`). File reports here using [REPORT_TEMPLATE.md](REPORT_TEMPLATE.md). CI smoke is not interactive evidence.

| Path | Interactive filed | CI smoke filed | Notes |
| --- | --- | --- | --- |
| pipx Linux | 0 | 0 | CI wheel smoke does not replace interactive reports |
| pipx Windows | 0 | 0 | Partial interactive evidence acceptable while collecting 3× |
| pipx WSL2 | 0 | 0 | Run `scripts/smoke/smoke_wsl_layout.sh` inside Ubuntu |
| source Linux | 0 | 0 | CI only until interactive reports land |
| source Windows | 0 | 1 | Contributor smoke + interactive reports |
| source WSL2 | 0 | 0 | clone on Linux home, project on `/mnt/c`; `grinta doctor` + interrupt test |

_Last updated by `ga_onboarding_gate.py` on 2026-07-08 12:08 UTC._

See [RELEASE_CHECKLIST.md](../RELEASE_CHECKLIST.md) when preparing a future release.
