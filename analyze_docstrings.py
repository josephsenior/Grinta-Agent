#!/usr/bin/env python3
"""Analyze docstring coverage across specified modules."""

import ast
import sys
from pathlib import Path
from typing import Any

def get_functions_and_classes(tree: ast.AST, module_path: str = "") -> list[dict[str, Any]]:
    """Extract all functions and classes with docstring info."""
    items = []
    
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            has_docstring = ast.get_docstring(node) is not None
            items.append({
                "type": "function",
                "name": node.name,
                "has_docstring": has_docstring,
                "lineno": node.lineno,
                "is_private": node.name.startswith("_"),
            })
        elif isinstance(node, ast.ClassDef):
            has_docstring = ast.get_docstring(node) is not None
            items.append({
                "type": "class",
                "name": node.name,
                "has_docstring": has_docstring,
                "lineno": node.lineno,
                "is_private": node.name.startswith("_"),
            })
    
    return items

def analyze_file(filepath: Path) -> dict[str, Any]:
    """Analyze a single Python file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        
        tree = ast.parse(source)
        items = get_functions_and_classes(tree, str(filepath))
        
        return {
            "filepath": str(filepath),
            "error": None,
            "items": items,
            "total": len(items),
            "documented": sum(1 for item in items if item["has_docstring"]),
            "undocumented": sum(1 for item in items if not item["has_docstring"]),
        }
    except Exception as e:
        return {
            "filepath": str(filepath),
            "error": str(e),
            "items": [],
        }

def main():
    """Main entry point."""
    base_path = Path("c:/Users/GIGABYTE/Desktop/Forge/forge")
    
    # Focus on the core modules specified for docstring coverage
    modules = [
        "metasop",
        "memory", 
        "runtime",
        "utils",
        "server/routes",
    ]
    
    all_results = []
    
    for module in modules:
        module_path = base_path / module
        if not module_path.exists():
            print(f"Module not found: {module_path}")
            continue
        
        py_files = list(module_path.rglob("*.py"))
        
        for py_file in py_files:
            # Skip __pycache__ and test files for now
            if "__pycache__" in py_file.parts or py_file.name.startswith("test_"):
                continue
            
            result = analyze_file(py_file)
            if result["error"]:
                print(f"ERROR in {py_file}: {result['error']}")
                continue
            
            all_results.append(result)
    
    # Print summary
    print("\n" + "=" * 80)
    print("DOCSTRING COVERAGE ANALYSIS")
    print("=" * 80)
    
    total_items = 0
    total_documented = 0
    undocumented_functions = []
    
    for result in all_results:
        if result["error"]:
            continue
        
        if result["total"] == 0:
            continue
            
        total_items += result["total"]
        total_documented += result["documented"]
        
        # Show files with undocumented items
        if result["undocumented"] > 0:
            rel_path = result["filepath"].replace(str(base_path) + "\\", "")
            print(f"\n{rel_path}")
            print(f"  Total: {result['total']} | Documented: {result['documented']} | Undocumented: {result['undocumented']}")
            
            for item in result["items"]:
                if not item["has_docstring"]:
                    item_type = "FUNC" if item["type"] == "function" else "CLASS"
                    privacy = "private" if item["is_private"] else "public"
                    print(f"    [{item_type}] {item['name']} (line {item['lineno']}) [{privacy}]")
                    
                    if item["is_private"] and item["type"] == "function":
                        undocumented_functions.append({
                            "file": rel_path,
                            "name": item["name"],
                            "line": item["lineno"],
                        })
    
    print("\n" + "=" * 80)
    print(f"OVERALL COVERAGE: {total_documented}/{total_items} ({100*total_documented/total_items if total_items else 0:.1f}%)")
    print(f"Undocumented private functions needing attention: {len(undocumented_functions)}")
    print("=" * 80)
    
    if undocumented_functions:
        print("\nPrivate functions to document:")
        for func in undocumented_functions:
            print(f"  {func['file']} :: {func['name']} (line {func['line']})")

if __name__ == "__main__":
    main()
