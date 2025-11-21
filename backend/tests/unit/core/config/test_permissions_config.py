from forge.core.config.permissions_config import (
    PermissionCategory,
    PermissionsConfig,
    RiskLevel,
)


def test_permissions_get_preset_levels():
    supervised = PermissionsConfig.get_preset("supervised")
    assert supervised.autonomy_level == "supervised"
    balanced = PermissionsConfig.get_preset("balanced")
    assert balanced.warn_at_cost == 7.0
    full = PermissionsConfig.get_preset("full")
    assert full.autonomy_level == "full"
    assert full.max_cost_per_task is None


def test_check_permission_category_denied():
    config = PermissionsConfig(file_read_enabled=False)
    allowed, reason = config.check_permission(PermissionCategory.FILE_READ, "read_file")
    assert not allowed
    assert reason == "File read operations are disabled"


def test_check_permission_specific_operation_denied():
    config = PermissionsConfig(git_allow_force_push=False)
    allowed, reason = config.check_permission(PermissionCategory.GIT, "git_force_push")
    assert not allowed
    assert reason == "Force push is not allowed"


def test_check_permission_allowed_when_enabled():
    config = PermissionsConfig(shell_allow_sudo=True)
    allowed, reason = config.check_permission(PermissionCategory.SHELL, "sudo_command")
    assert allowed
    assert reason is None
