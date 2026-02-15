import libcst as cst
import os
import sys

class LoggingFStringTransformer(cst.CSTTransformer):
    def __init__(self):
        self.logger_methods = {'debug', 'info', 'warning', 'error', 'exception', 'critical'}

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        # Check if the call is logger.method(...)
        if not (
            isinstance(updated_node.func, cst.Attribute) and
            isinstance(updated_node.func.value, cst.Name) and
            updated_node.func.value.value == 'logger' and
            updated_node.func.attr.value in self.logger_methods
        ):
            return updated_node

        # Check if there are arguments
        if not updated_node.args:
            return updated_node

        # Check if the first argument is an f-string
        first_arg = updated_node.args[0].value
        if not isinstance(first_arg, cst.FormattedString):
            return updated_node

        # Transform f-string to (format_string, *expressions)
        format_parts = []
        expressions = []

        for part in first_arg.parts:
            if isinstance(part, cst.FormattedStringText):
                # Escape % in literal text
                format_parts.append(part.value.replace('%', '%%'))
            elif isinstance(part, cst.FormattedStringExpression):
                # Determine placeholder based on format spec if present
                placeholder = '%s'
                if part.format_spec:
                    # Simple mapping for common format specs
                    spec_str = "".join(p.value for p in part.format_spec.parts if isinstance(p, cst.FormattedStringText))
                    if 'f' in spec_str:
                        placeholder = f'%{spec_str}'
                    elif 'd' in spec_str:
                        placeholder = f'%{spec_str}'
                
                format_parts.append(placeholder)
                expressions.append(cst.Arg(value=part.expression))

        format_string = "".join(format_parts)
        
        # Create new arguments list: [new_format_string, *old_expressions, *remaining_args]
        new_args = [
            cst.Arg(value=cst.SimpleString(f'"{format_string}"')),
            *expressions,
            *updated_node.args[1:]
        ]

        return updated_node.with_changes(args=new_args)

def process_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    try:
        tree = cst.parse_module(code)
        transformer = LoggingFStringTransformer()
        modified_tree = tree.visit(transformer)
        
        if not tree.deep_equals(modified_tree):
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(modified_tree.code)
            return True
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    
    return False

if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else 'backend'
    files_modified = 0
    
    for root, _, files in os.walk(target_dir):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                if process_file(path):
                    print(f"Fixed: {path}")
                    files_modified += 1
    
    print(f"\nDone! Modified {files_modified} files.")
