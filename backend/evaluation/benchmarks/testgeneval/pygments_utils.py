import re
from pygments.lexers.python import PythonLexer


def tokenize_code(code):
    lexer = PythonLexer()
    return process_pygments_tokens(lexer.get_tokens(code))


def process_pygments_tokens(tokens):
    new_tokens = _filter_relevant_tokens(tokens)
    return _process_string_tokens(new_tokens)


def _filter_relevant_tokens(tokens):
    """Filter out irrelevant tokens like whitespace and text."""
    return [
        token[1]
        for token in tokens
        if (str(token[0]) != "Token.Text" or not re.match("\\s+", token[1]))
        and str(token[0]) != "Token.Text.Whitespace"
    ]


def _process_string_tokens(new_tokens):
    """Process tokens to handle string patterns."""
    new_tokens_final = []
    i = 0

    while i < len(new_tokens) - 2:
        if _is_string_pattern(new_tokens, i):
            new_tokens_final.append('"STR"')
            i += 3
        else:
            new_tokens_final.append(new_tokens[i])
            i += 1

    # Add remaining tokens
    remaining_tokens = (
        new_tokens[len(new_tokens) - 2 :] if len(new_tokens) >= 2 else new_tokens
    )
    new_tokens_final.extend(remaining_tokens)

    return new_tokens_final


def _is_string_pattern(tokens, i):
    """Check if tokens form a string pattern: quote, STR, quote."""
    return tokens[i] == '"' and tokens[i + 1] == "STR" and tokens[i + 2] == '"'
