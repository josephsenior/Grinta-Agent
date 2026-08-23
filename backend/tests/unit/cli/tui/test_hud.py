"""Headless TUI — hud."""

from backend.tests.unit.cli.tui._shared import (
    GrintaScreen,
    GrintaTUIApp,
    Label,
    MagicMock,
    RichConsole,
    Select,
    SimpleNamespace,
    _get_screen,
    asyncio,
    pytest,
)


def test_hud_model_entry_resolution_is_cached_per_model(monkeypatch):
    """Periodic HUD paints must not rebuild the provider catalog."""
    from backend.cli.tui.screen.state import ScreenStateMixin

    builds = []
    entry = SimpleNamespace(name='model-a')

    def build_entries(*, provider):
        builds.append(provider)
        return {provider: [entry]}

    monkeypatch.setattr(
        'backend.cli.settings.get_current_model',
        lambda _config: _config.model,
    )
    monkeypatch.setattr(
        'backend.inference.catalog.provider_catalog.build_model_entries_by_provider',
        build_entries,
    )
    monkeypatch.setattr(
        'backend.inference.capabilities.param_profiles.resolve_model_entry_for_capabilities',
        lambda model, provider, *, fallback: fallback,
    )
    screen = ScreenStateMixin()
    screen._config = SimpleNamespace(model='model-a')
    screen._hud = SimpleNamespace(state=SimpleNamespace(model='model-a'))
    screen._current_llm_provider = lambda: 'provider-a'

    assert ScreenStateMixin._resolve_hud_model_entry(screen) is entry
    assert ScreenStateMixin._resolve_hud_model_entry(screen) is entry
    assert builds == ['provider-a']

    screen._config.model = 'model-b'
    ScreenStateMixin._resolve_hud_model_entry(screen)
    assert builds == ['provider-a', 'provider-a']


def test_hud_pulse_only_repaints_status_label():
    """Animation ticks should not rebuild selects or the rest of the HUD."""
    from backend.cli.tui.screen.state import ScreenStateMixin

    calls = []
    screen = ScreenStateMixin()
    screen._is_unmounted = False
    screen._hud = SimpleNamespace(state=SimpleNamespace(agent_state_label='Running'))
    screen._hud_pulse_frame = 0
    screen._render_hud_status_label = lambda: calls.append('status')
    screen._render_hud_bar = lambda: calls.append('full')

    ScreenStateMixin._tick_hud_running_pulse(screen)

    assert calls == ['status']
    assert screen._hud_pulse_frame == 1


@pytest.mark.asyncio
async def test_tui_hud_bar_shows_workspace_path(mock_config):
    console = RichConsole()
    loop = asyncio.get_running_loop()
    app = GrintaTUIApp(config=mock_config, console=console, loop=loop)

    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()

        s = _get_screen(app)
        s._config = mock_config
        s._render_hud_bar()
        await pilot.pause()

        stats = s.query_one('#hud-line-2-ws', Label)
        rendered = str(stats.content)
        assert 'Ws:' in rendered
        assert '● Grinta' in rendered
        assert '…/' in rendered or 'Ws:' in rendered


@pytest.mark.asyncio
async def test_tui_update_hud_state(mock_config, monkeypatch):
    """Verify update_hud folds runtime info into the two-line HUD."""
    console = RichConsole()
    loop = asyncio.get_running_loop()
    app = GrintaTUIApp(config=mock_config, console=console, loop=loop)

    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()

        s = _get_screen(app)
        s._hud.update_agent_state('Running')
        s.update_hud()
        await pilot.pause()

        stats = s.query_one('#hud-line-1', Label)
        activity = s.query_one('#hud-line-2', Label)
        help_label = s.query_one('#hud-line-1-help', Label)
        assert 'Running' in str(stats.content)
        assert 'Ctx:' in str(activity.content)
        assert 'Help' in str(help_label.content)


@pytest.mark.asyncio
async def test_tui_hud_bar_shows_accumulated_and_context_tokens(mock_config):
    console = RichConsole()
    loop = asyncio.get_running_loop()
    app = GrintaTUIApp(config=mock_config, console=console, loop=loop)

    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()

        s = _get_screen(app)
        s._hud.state.total_tokens = 430
        s._hud.state.context_tokens = 430
        s._hud.state.context_limit = 8192
        s._render_hud_bar()
        await pilot.pause()

        stats = s.query_one('#hud-line-2', Label)
        rendered = str(stats.content)
        assert 'Ctx: 430/8.2K' in rendered
        assert '%' in rendered


@pytest.mark.asyncio
async def test_tui_hud_reasoning_hidden_when_model_has_no_control(
    mock_config, monkeypatch
):
    from backend.inference.capabilities.param_profiles import (
        resolve_model_entry_for_capabilities,
    )

    console = RichConsole()
    loop = asyncio.get_running_loop()
    mock_config.get_llm_config.return_value.model = 'openai/gpt-4.1'
    mock_config.get_llm_config.return_value.provider = 'openrouter'
    app = GrintaTUIApp(config=mock_config, console=console, loop=loop)
    entry = resolve_model_entry_for_capabilities('openai/gpt-4.1', 'openrouter')
    monkeypatch.setattr(GrintaScreen, '_resolve_hud_model_entry', lambda self: entry)

    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()

        s = _get_screen(app)
        s._config = mock_config
        s._render_hud_bar()
        await pilot.pause()

        reasoning = s.query_one('#hud-reasoning', Select)
        label = s.query_one('#hud-label-reasoning', Label)
        assert reasoning.display is False
        assert label.display is False


@pytest.mark.asyncio
async def test_tui_hud_reasoning_visible_when_model_supports_control(
    mock_config, monkeypatch
):
    from backend.inference.capabilities.param_profiles import (
        resolve_model_entry_for_capabilities,
    )

    console = RichConsole()
    loop = asyncio.get_running_loop()
    mock_config.get_llm_config.return_value.model = 'mimo-v2.5-free'
    mock_config.get_llm_config.return_value.provider = 'opencode'
    app = GrintaTUIApp(config=mock_config, console=console, loop=loop)
    entry = resolve_model_entry_for_capabilities('mimo-v2.5-free', 'opencode')
    monkeypatch.setattr(GrintaScreen, '_resolve_hud_model_entry', lambda self: entry)

    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()

        s = _get_screen(app)
        s._config = mock_config
        s._render_hud_bar()
        await pilot.pause()

        reasoning = s.query_one('#hud-reasoning', Select)
        label = s.query_one('#hud-label-reasoning', Label)
        assert reasoning.display is True
        assert label.display is True


@pytest.mark.asyncio
async def test_tui_hud_reasoning_select_syncs_from_config(mock_config, monkeypatch):
    console = RichConsole()
    loop = asyncio.get_running_loop()
    mock_config.get_llm_config.return_value.reasoning_effort = 'high'
    app = GrintaTUIApp(config=mock_config, console=console, loop=loop)
    monkeypatch.setattr(
        GrintaScreen,
        '_hud_reasoning_select_options',
        lambda self: [
            ('Default', ''),
            ('Low', 'low'),
            ('Medium', 'medium'),
            ('High', 'high'),
        ],
    )

    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()

        s = _get_screen(app)
        s._config = mock_config
        s._render_hud_bar()
        await pilot.pause()

        reasoning = s.query_one('#hud-reasoning', Select)
        assert reasoning.value == 'high'


@pytest.mark.asyncio
async def test_tui_hud_reasoning_sync_does_not_apply_setting(mock_config, monkeypatch):
    console = RichConsole()
    loop = asyncio.get_running_loop()
    mock_config.get_llm_config.return_value.reasoning_effort = 'high'
    app = GrintaTUIApp(config=mock_config, console=console, loop=loop)
    monkeypatch.setattr(
        GrintaScreen,
        '_hud_reasoning_select_options',
        lambda self: [('XHigh', 'xhigh'), ('High', 'high')],
    )
    update_calls = []
    monkeypatch.setattr(
        'backend.cli.settings.update_model',
        lambda *args, **kwargs: update_calls.append((args, kwargs)),
    )

    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()

        s = _get_screen(app)
        s.notify = MagicMock()  # type: ignore[method-assign]
        s._config = mock_config
        s._render_hud_bar()
        await pilot.pause()
        await pilot.pause()

        reasoning = s.query_one('#hud-reasoning', Select)
        assert reasoning.value == 'high'
        assert update_calls == []
        s.notify.assert_not_called()


@pytest.mark.asyncio
async def test_tui_hud_reasoning_effort_persists(mock_config, monkeypatch):
    console = RichConsole()
    loop = asyncio.get_running_loop()
    monkeypatch.setattr(GrintaScreen, '_start_background_bootstrap', lambda self: None)
    app = GrintaTUIApp(config=mock_config, console=console, loop=loop)
    monkeypatch.setattr(
        GrintaScreen,
        '_hud_reasoning_select_options',
        lambda self: [('Default', ''), ('Low', 'low'), ('High', 'high')],
    )

    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()

        s = _get_screen(app)
        s._config = mock_config
        s._apply_hud_reasoning_effort('low')
        await pilot.pause()

        from backend.cli.settings import get_persisted_reasoning_effort

        assert get_persisted_reasoning_effort() == 'low'


@pytest.mark.asyncio
async def test_tui_hud_autonomy_selector_updates_controller(mock_config):
    console = RichConsole()
    loop = asyncio.get_running_loop()
    app = GrintaTUIApp(config=mock_config, console=console, loop=loop)

    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()

        s = _get_screen(app)
        controller = SimpleNamespace(
            autonomy_controller=SimpleNamespace(autonomy_level='balanced')
        )
        s._controller = controller  # type: ignore[assignment]
        autonomy = s.query_one('#hud-autonomy', Select)
        autonomy.value = 'full'
        await pilot.pause()

        assert controller.autonomy_controller.autonomy_level == 'full'
        assert s._hud.state.autonomy_level == 'full'


@pytest.mark.asyncio
async def test_tui_hud_autonomy_persists(mock_config):
    console = RichConsole()
    loop = asyncio.get_running_loop()
    app = GrintaTUIApp(config=mock_config, console=console, loop=loop)

    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()

        s = _get_screen(app)
        s._config = mock_config
        s._apply_autonomy_level('full')
        await pilot.pause()

        from backend.cli.settings import get_persisted_autonomy_level

        assert get_persisted_autonomy_level('agent') == 'full'


@pytest.mark.asyncio
async def test_tui_hud_autonomy_sync_uses_agent_config_without_applying_default(
    mock_config, monkeypatch
):
    console = RichConsole()
    loop = asyncio.get_running_loop()
    agent_config = SimpleNamespace(mode='agent', autonomy_level='full')
    mock_config.get_agent_config.return_value = agent_config
    app = GrintaTUIApp(config=mock_config, console=console, loop=loop)

    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()

        s = _get_screen(app)
        s.notify = MagicMock()  # type: ignore[method-assign]
        s._hud.update_autonomy('balanced')
        s._render_hud_bar()
        await pilot.pause()
        await pilot.pause()

        autonomy = s.query_one('#hud-autonomy', Select)
        assert autonomy.value == 'full'
        assert s._hud.state.autonomy_level == 'full'
        assert agent_config.autonomy_level == 'full'
        s.notify.assert_not_called()


@pytest.mark.asyncio
async def test_tui_hud_autonomy_render_shows_runtime_level(
    mock_config, monkeypatch, tmp_path
):
    settings_file = tmp_path / 'settings.json'
    settings_file.write_text(
        '{"agent":{"Orchestrator":{"autonomy_level":"full"}}}\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(
        'backend.cli.settings.storage._settings_path',
        lambda: settings_file,
    )
    console = RichConsole()
    loop = asyncio.get_running_loop()
    agent_config = SimpleNamespace(mode='agent', autonomy_level='balanced')
    mock_config.default_agent = 'Orchestrator'
    mock_config.get_agent_config.return_value = agent_config
    app = GrintaTUIApp(config=mock_config, console=console, loop=loop)

    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()

        s = _get_screen(app)
        s.notify = MagicMock()  # type: ignore[method-assign]
        s._render_hud_bar()
        await pilot.pause()

        autonomy = s.query_one('#hud-autonomy', Select)
        assert autonomy.value == 'balanced'
        assert s._hud.state.autonomy_level == 'balanced'
        s.notify.assert_not_called()


@pytest.mark.asyncio
async def test_tui_hud_autonomy_persists_when_runtime_already_matches(
    mock_config, monkeypatch, tmp_path
):
    """TUI choice must write settings.json even when runtime already matches."""
    settings_file = tmp_path / 'settings.json'
    settings_file.write_text(
        '{"agent":{"Orchestrator":{"autonomy_level":"conservative"}}}\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(
        'backend.cli.settings.storage._settings_path',
        lambda: settings_file,
    )
    console = RichConsole()
    loop = asyncio.get_running_loop()
    agent_config = SimpleNamespace(mode='agent', autonomy_level='full')
    mock_config.default_agent = 'Orchestrator'
    mock_config.get_agent_config.return_value = agent_config
    controller = SimpleNamespace(
        autonomy_controller=SimpleNamespace(autonomy_level='full')
    )
    monkeypatch.setattr(GrintaScreen, '_start_background_bootstrap', lambda self: None)
    app = GrintaTUIApp(config=mock_config, console=console, loop=loop)

    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()

        s = _get_screen(app)
        s._controller = controller  # type: ignore[assignment]
        s._apply_autonomy_level('full')
        await pilot.pause()

        from backend.cli.settings import get_persisted_autonomy_level

        assert get_persisted_autonomy_level('Orchestrator') == 'full'
        autonomy = s.query_one('#hud-autonomy', Select)
        assert autonomy.value == 'full'
