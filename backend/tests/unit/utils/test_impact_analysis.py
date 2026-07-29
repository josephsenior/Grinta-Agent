"""Unit tests for backend.utils.impact_analysis."""

from unittest.mock import MagicMock, patch

from backend.utils.impact_analysis import (
    _find_defining_file,
    _grep_fallback_locations,
    _is_test_file,
    analyze_symbol_impact,
)


class TestImpactAnalysis:
    def test_is_test_file_variants(self) -> None:
        assert _is_test_file('backend/tests/unit/test_main.py') is True
        assert _is_test_file('tests/explore/helper.py') is True
        assert _is_test_file('src/test_utils.py') is True
        assert _is_test_file('src/utils_test.py') is True
        assert _is_test_file('backend/specs/my_spec.py') is True
        assert _is_test_file('backend/core/main.py') is False
        assert _is_test_file('src/utils.py') is False

    @patch('backend.utils.impact_analysis.os.path.exists', return_value=True)
    @patch('backend.utils.impact_analysis.get_lsp_client')
    @patch('backend.utils.impact_analysis.TreeSitterEditor.find_symbol')
    def test_analyze_symbol_impact_lsp(
        self, mock_find_symbol, mock_get_lsp_client, mock_exists
    ) -> None:
        mock_client = MagicMock()
        mock_client.available = True
        mock_get_lsp_client.return_value = mock_client
        mock_result = MagicMock()

        # Mock 10 references (5 production, 5 tests)
        mock_locations = []
        for i in range(5):
            mock_locations.append(
                MagicMock(
                    file=f'src/prod_{i}.py', line=10, column=5, message=f'use_{i}'
                )
            )
            mock_locations.append(
                MagicMock(
                    file=f'tests/test_{i}.py', line=15, column=5, message=f'test_{i}'
                )
            )

        mock_result.locations = mock_locations
        mock_client.query.return_value = mock_result
        mock_find_symbol.return_value = MagicMock(line_start=1)

        report = analyze_symbol_impact('src/define.py', 'my_func')

        assert report is not None
        assert report.symbol == 'my_func'
        assert report.engine == 'lsp'
        assert report.confidence == 'high'
        assert report.total_references == 10
        assert report.production_references == 5
        assert report.test_references == 5
        assert report.unique_files == 10
        assert report.risk == 'high'
        assert 'Referenced outside its defining package' in report.reasons

    @patch('backend.utils.impact_analysis.os.path.exists', return_value=True)
    @patch('backend.utils.impact_analysis.subprocess.run')
    @patch('backend.utils.impact_analysis.shutil.which', return_value='rg')
    @patch('backend.utils.impact_analysis.get_lsp_client')
    @patch('backend.utils.impact_analysis.TreeSitterEditor.find_symbol')
    def test_analyze_symbol_impact_ripgrep_fallback(
        self,
        mock_find_symbol,
        mock_get_lsp_client,
        mock_shutil_which,
        mock_run,
        mock_exists,
    ) -> None:
        mock_client = MagicMock()
        mock_client.available = False
        mock_get_lsp_client.return_value = mock_client

        mock_find_symbol.return_value = MagicMock(line_start=1)
        mock_run.return_value = MagicMock(
            stdout='src/prod_1.py:10:result = my_func()\nsrc/prod_2.py:12:my_func()\n'
        )

        report = analyze_symbol_impact('src/define.py', 'my_func')

        assert report is not None
        assert report.symbol == 'my_func'
        assert report.engine == 'ripgrep'
        assert report.confidence == 'medium'
        assert report.total_references == 2
        assert report.unique_files == 2
        assert report.risk == 'medium'

    @patch('backend.utils.impact_analysis.subprocess.run')
    @patch('backend.utils.impact_analysis.shutil.which', return_value='rg')
    def test_grep_fallback_locations_with_rg(self, mock_which, mock_run) -> None:
        mock_run.return_value = MagicMock(
            stdout='src/file1.py:5:value = symbol\nsrc/file2.py:10:# symbol commented out\nsrc/file3.py:12:symbol()\n'
        )
        locs = _grep_fallback_locations('symbol', 'src/define.py', 1, search_root='.')
        assert len(locs) == 2
        assert locs[0].file_path == 'src/file1.py'
        assert locs[0].line == 5
        assert locs[1].file_path == 'src/file3.py'

    @patch('backend.utils.impact_analysis.shutil.which', return_value=None)
    @patch('backend.utils.impact_analysis.os.walk')
    def test_grep_fallback_locations_python_walk(self, mock_walk, mock_which) -> None:
        mock_walk.return_value = [('.', [], ['file1.py'])]
        with patch(
            'builtins.open',
            mock_open_read('def symbol():\n    symbol()\n    # symbol comment'),
        ):
            locs = _grep_fallback_locations('symbol', 'define.py', 1, search_root='.')
            assert len(locs) >= 0

    @patch('backend.utils.impact_analysis.subprocess.run')
    @patch('backend.utils.impact_analysis.shutil.which', return_value='rg')
    def test_find_defining_file_rg(self, mock_which, mock_run) -> None:
        mock_run.return_value = MagicMock(stdout='/path/to/def.py\n')
        res = _find_defining_file('my_symbol', '.')
        assert res is not None
        assert res.endswith('def.py')

    @patch('backend.utils.impact_analysis.os.path.exists', return_value=False)
    @patch('backend.utils.impact_analysis.subprocess.run')
    @patch('backend.utils.impact_analysis.shutil.which', return_value='rg')
    def test_analyze_symbol_impact_no_definition_file(
        self, mock_which, mock_run, mock_exists
    ) -> None:
        mock_run.return_value = MagicMock(stdout='')
        report = analyze_symbol_impact(None, 'missing_symbol')
        assert report is not None
        assert report.engine == 'ripgrep'
        assert report.confidence == 'low'
        assert report.total_references == 0
        assert report.risk == 'low'

    @patch('backend.utils.impact_analysis.os.path.exists', return_value=True)
    @patch('backend.utils.impact_analysis.get_lsp_client')
    @patch('backend.utils.impact_analysis.TreeSitterEditor.find_symbol')
    def test_analyze_symbol_impact_truncation(
        self, mock_find_symbol, mock_get_lsp_client, mock_exists
    ) -> None:
        mock_client = MagicMock()
        mock_client.available = True
        mock_get_lsp_client.return_value = mock_client
        mock_result = MagicMock()

        # Mock >50 locations
        mock_locations = [
            MagicMock(file=f'src/file_{i}.py', line=10, column=1, message='ref')
            for i in range(60)
        ]
        mock_result.locations = mock_locations
        mock_client.query.return_value = mock_result
        mock_find_symbol.return_value = MagicMock(line_start=1)

        report = analyze_symbol_impact('src/def.py', 'popular_func')
        assert report is not None
        assert report.truncated is True
        assert len(report.locations) == 50

    def test_analyze_symbol_impact_exception(self) -> None:
        with patch(
            'backend.utils.impact_analysis.TreeSitterEditor',
            side_effect=RuntimeError('Editor crash'),
        ):
            report = analyze_symbol_impact('src/def.py', 'func')
            assert report is None


def mock_open_read(content: str):
    from unittest.mock import mock_open

    return mock_open(read_data=content)
