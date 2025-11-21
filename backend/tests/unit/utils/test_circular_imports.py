import os
import re
import unittest


class TestCircularImports(unittest.TestCase):
    """Test to detect circular imports in the codebase."""

    def test_no_circular_imports_in_key_modules(self):
        """Test that there are no circular imports in key modules that were previously problematic.

        This test specifically checks the modules that were involved in a previous circular import issue:
        - forge.utils.prompt
        - forge.agenthub.codeact_agent.tools.bash
        - forge.agenthub.codeact_agent.tools.prompt
        - forge.memory.memory
        - forge.memory.conversation_memory
        """
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        module_paths = {
            "forge.utils.prompt": os.path.join(project_root, "Forge/utils/prompt.py"),
            "forge.agenthub.codeact_agent.tools.bash": os.path.join(
                project_root, "Forge/agenthub/codeact_agent/tools/bash.py"
            ),
            "forge.agenthub.codeact_agent.tools.prompt": os.path.join(
                project_root, "Forge/agenthub/codeact_agent/tools/prompt.py"
            ),
            "forge.memory.memory": os.path.join(project_root, "Forge/memory/memory.py"),
            "forge.memory.conversation_memory": os.path.join(
                project_root, "Forge/memory/conversation_memory.py"
            ),
        }
        if circular_imports := self._find_circular_imports(module_paths):
            circular_import_str = "\n".join(
                [
                    f"{module1} -> {module2} -> {module1}"
                    for module1, module2 in circular_imports
                ]
            )
            self.fail(f"Circular imports detected:\n{circular_import_str}")

    def _find_circular_imports(
        self, module_paths: dict[str, str]
    ) -> list[tuple[str, str]]:
        """Find circular imports between modules.

        Args:
            module_paths: Dictionary mapping module names to file paths

        Returns:
            List of tuples (module1, module2) where module1 imports module2 and module2 imports module1
        """
        module_imports = {}
        for module_name, file_path in module_paths.items():
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    source_code = f.read()
                import_lines = [
                    line.strip()
                    for line in source_code.split("\n")
                    if line.strip().startswith(("import ", "from "))
                    and (not line.strip().startswith("# "))
                ]
                imported_modules = []
                for line in import_lines:
                    if line.startswith("import "):
                        parts = line[7:].split(",")
                        for part in parts:
                            module_part = part.strip().split(" as ")[0].strip()
                            if module_part.startswith("forge."):
                                imported_modules.append(module_part)
                    elif line.startswith("from "):
                        module_part = line[5:].split(" import ")[0].strip()
                        if module_part.startswith("forge."):
                            imported_modules.append(module_part)
                module_imports[module_name] = imported_modules
        circular_imports: list[tuple[str, str]] = []
        for module1, imports1 in module_imports.items():
            circular_imports.extend(
                (
                    (module1, module2)
                    for module2 in imports1
                    if module2 in module_imports and module1 in module_imports[module2]
                )
            )
        return circular_imports

    def test_specific_circular_import_pattern(self):
        """Test for the specific circular import pattern that caused the issue in the stack trace.

        The problematic pattern was:
        forge.utils.prompt imports from forge.agenthub.codeact_agent.tools.bash
        forge.agenthub.codeact_agent.tools.bash imports from forge.agenthub.codeact_agent.tools.prompt
        forge.agenthub.codeact_agent.tools.prompt imports from forge.utils.prompt
        """
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        prompt_path = os.path.join(project_root, "Forge/utils/prompt.py")
        bash_path = os.path.join(
            project_root, "Forge/agenthub/codeact_agent/tools/bash.py"
        )
        tools_prompt_path = os.path.join(
            project_root, "Forge/agenthub/codeact_agent/tools/prompt.py"
        )
        if not all(
            (
                os.path.exists(path)
                for path in [prompt_path, bash_path, tools_prompt_path]
            )
        ):
            self.skipTest("One or more required files do not exist")
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_code = f.read()
        with open(bash_path, "r", encoding="utf-8") as f:
            bash_code = f.read()
        with open(tools_prompt_path, "r", encoding="utf-8") as f:
            tools_prompt_code = f.read()
        prompt_imports_bash = (
            re.search(
                "from forge\\.agenthub\\.codeact_agent\\.tools\\.bash import",
                prompt_code,
            )
            is not None
        )
        bash_imports_tools_prompt = (
            re.search(
                "from forge\\.agenthub\\.codeact_agent\\.tools\\.prompt import",
                bash_code,
            )
            is not None
        )
        tools_prompt_imports_prompt = (
            re.search("from forge\\.utils\\.prompt import", tools_prompt_code)
            is not None
        )
        if (
            prompt_imports_bash
            and bash_imports_tools_prompt
            and tools_prompt_imports_prompt
        ):
            self.fail(
                "Circular import pattern detected:\nforge.utils.prompt imports from forge.agenthub.codeact_agent.tools.bash\nforge.agenthub.codeact_agent.tools.bash imports from forge.agenthub.codeact_agent.tools.prompt\nforge.agenthub.codeact_agent.tools.prompt imports from forge.utils.prompt"
            )

    def test_detect_circular_imports_in_server_modules(self):
        """Test for circular imports in the server modules that were involved in the stack trace.

        The problematic modules were:
        - forge.server.shared
        - forge.server.conversation_manager.conversation_manager
        - forge.server.session.agent_session
        - forge.server.session
        - forge.server.session.session
        """
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        module_paths = {
            "forge.server.shared": os.path.join(project_root, "Forge/server/shared.py"),
            "forge.server.conversation_manager.conversation_manager": os.path.join(
                project_root,
                "Forge/server/conversation_manager/conversation_manager.py",
            ),
            "forge.server.session.agent_session": os.path.join(
                project_root, "Forge/server/session/agent_session.py"
            ),
            "forge.server.session.__init__": os.path.join(
                project_root, "Forge/server/session/__init__.py"
            ),
            "forge.server.session.session": os.path.join(
                project_root, "Forge/server/session/session.py"
            ),
        }
        if circular_imports := self._find_circular_imports(module_paths):
            circular_import_str = "\n".join(
                [
                    f"{module1} -> {module2} -> {module1}"
                    for module1, module2 in circular_imports
                ]
            )
            self.fail(
                f"Circular imports detected in server modules:\n{circular_import_str}"
            )

    def test_detect_circular_imports_in_mcp_modules(self):
        """Test for circular imports in the MCP modules that were involved in the stack trace.

        The problematic modules were:
        - forge.mcp
        - forge.mcp.utils
        - forge.memory.memory
        """
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        module_paths = {
            "forge.mcp.__init__": os.path.join(project_root, "Forge/mcp/__init__.py"),
            "forge.mcp.utils": os.path.join(project_root, "Forge/mcp/utils.py"),
            "forge.memory.memory": os.path.join(project_root, "Forge/memory/memory.py"),
        }
        if circular_imports := self._find_circular_imports(module_paths):
            circular_import_str = "\n".join(
                [
                    f"{module1} -> {module2} -> {module1}"
                    for module1, module2 in circular_imports
                ]
            )
            self.fail(
                f"Circular imports detected in MCP modules:\n{circular_import_str}"
            )

    def test_detect_complex_circular_import_chains(self):
        """Test for complex circular import chains involving multiple modules.

        This test checks for circular dependencies that involve more than two modules,
        such as A imports B, B imports C, and C imports A.
        """
        project_root = self._get_project_root()
        modules = self._get_test_modules()
        module_paths = self._build_module_paths(project_root, modules)
        import_graph = self._build_import_graph(module_paths)

        if circular_chains := self._find_circular_chains(import_graph):
            circular_chain_str = "\n".join(
                [" -> ".join(chain) for chain in circular_chains]
            )
            self.fail(f"Complex circular import chains detected:\n{circular_chain_str}")

    def _get_project_root(self):
        """Get the project root directory."""
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

    def _get_test_modules(self):
        """Get the list of modules to test."""
        return [
            "forge.utils.prompt",
            "forge.agenthub.codeact_agent.tools.bash",
            "forge.agenthub.codeact_agent.tools.prompt",
            "forge.memory.memory",
            "forge.memory.conversation_memory",
            "forge.server.shared",
            "forge.server.conversation_manager.conversation_manager",
            "forge.server.session.agent_session",
            "forge.server.session.__init__",
            "forge.server.session.session",
            "forge.mcp.__init__",
            "forge.mcp.utils",
        ]

    def _build_module_paths(self, project_root, modules):
        """Build module paths dictionary."""
        module_paths = {}
        for module in modules:
            file_path = self._get_module_file_path(project_root, module)
            if os.path.exists(file_path):
                module_paths[module] = file_path
        return module_paths

    def _get_module_file_path(self, project_root, module):
        """Get the file path for a module."""
        if module.endswith(".__init__"):
            module_path = module[:-9].replace(".", "/")
            return os.path.join(project_root, f"{module_path}/__init__.py")
        else:
            module_path = module.replace(".", "/")
            return os.path.join(project_root, f"{module_path}.py")

    def _build_import_graph(self, module_paths):
        """Build the import graph from module paths."""
        import_graph = {}
        for module_name, file_path in module_paths.items():
            imported_modules = self._extract_imported_modules(file_path)
            import_graph[module_name] = [
                m for m in imported_modules if m in module_paths
            ]
        return import_graph

    def _extract_imported_modules(self, file_path):
        """Extract imported modules from a file."""
        with open(file_path, "r", encoding="utf-8") as f:
            source_code = f.read()

        import_lines = self._get_import_lines(source_code)
        imported_modules = []

        for line in import_lines:
            if line.startswith("import "):
                imported_modules.extend(self._parse_import_statement(line))
            elif line.startswith("from "):
                imported_modules.extend(self._parse_from_statement(line))

        return imported_modules

    def _get_import_lines(self, source_code):
        """Get import lines from source code."""
        return [
            line.strip()
            for line in source_code.split("\n")
            if line.strip().startswith(("import ", "from "))
            and not line.strip().startswith("# ")
        ]

    def _parse_import_statement(self, line):
        """Parse an import statement."""
        parts = line[7:].split(",")
        imported_modules = []
        for part in parts:
            module_part = part.strip().split(" as ")[0].strip()
            if module_part.startswith("forge."):
                imported_modules.append(module_part)
        return imported_modules

    def _parse_from_statement(self, line):
        """Parse a from statement."""
        module_part = line[5:].split(" import ")[0].strip()
        return [module_part] if module_part.startswith("forge.") else []

    def _find_circular_chains(
        self, import_graph: dict[str, list[str]]
    ) -> list[list[str]]:
        """Find circular import chains in the import graph.

        Args:
            import_graph: Dictionary mapping module names to lists of imported modules

        Returns:
            List of circular import chains, where each chain is a list of module names
        """
        circular_chains = []

        def dfs(module: str, path: list[str], visited: set[str]):
            """Depth-first search to find circular import chains.

            Args:
                module: Current module being visited
                path: Current path in the DFS
                visited: Set of modules visited in the current DFS path
            """
            if module in visited:
                cycle_start = path.index(module)
                circular_chains.append(path[cycle_start:] + [module])
                return
            visited.add(module)
            path.append(module)
            for imported_module in import_graph.get(module, []):
                dfs(imported_module, path.copy(), visited.copy())

        for module in import_graph:
            dfs(module, [], set())
        return circular_chains


if __name__ == "__main__":
    unittest.main()
