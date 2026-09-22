"""
expression_utils.py
--------------------
These free functions figure out the C# *type* of a condition/expression
so the semantic checks can catch things like "if (x)" where x is an
int (must be bool), or "age > "5"" (comparing int to string).

Scope limitation (kept deliberately simple - see project README):
each side of a relational operator must be a single identifier or
literal (x > 5 is supported; x + 1 > 5 is not), since fully evaluating
arbitrary C# expressions is outside what "a simple if/switch compiler"
needs to do.

Used by both IfStatement and SwitchStatement in statements.py.
"""

from .tokens import TokenType, literal_type_of

ORDERABLE = {"int", "double", "char"}         # types that support <, >, <=, >=
EQUATABLE_ONLY = {"string", "bool"}           # types that only support ==, !=


def strip_redundant_parens(tokens):
    """Removes one redundant matching outer pair of parentheses, e.g.
    turns '(x > 5)' into 'x > 5', so conditions like 'if ((x > 5))' or
    '((a) && (b))' are still analyzed correctly."""
    while len(tokens) >= 2 and tokens[0].lexeme == "(" and tokens[-1].lexeme == ")":
        depth = 0
        wraps_all = True
        for i, t in enumerate(tokens):
            if t.lexeme == "(":
                depth += 1
            elif t.lexeme == ")":
                depth -= 1
                if depth == 0 and i != len(tokens) - 1:
                    wraps_all = False
                    break
        if wraps_all:
            tokens = tokens[1:-1]
        else:
            break
    return tokens


def split_top_level(tokens, lexemes):
    """Finds the index of the first token whose lexeme is in `lexemes`,
    ignoring anything nested inside parentheses (depth > 0). Used to find
    the top-level && / || / relational operator in a condition."""
    depth = 0
    for i, t in enumerate(tokens):
        if t.lexeme == "(":
            depth += 1
        elif t.lexeme == ")":
            depth -= 1
        elif depth == 0 and t.lexeme in lexemes:
            return i
    return -1


def get_operand_type(op_tokens, symbol_table, error_handler, line):
    """Type of a single operand: an identifier, a literal, or a negative literal."""
    if len(op_tokens) == 2 and op_tokens[0].lexeme == "-" and literal_type_of(op_tokens[1]) in ("int", "double"):
        return literal_type_of(op_tokens[1])
    if len(op_tokens) != 1:
        shown = " ".join(t.lexeme for t in op_tokens) if op_tokens else "(empty)"
        error_handler.report(
            "SYNTAX",
            f"Unsupported expression '{shown}'; only a single identifier or literal is supported here.",
            line,
        )
        return None
    tok = op_tokens[0]
    if tok.type == TokenType.IDENTIFIER:
        if symbol_table.is_declared(tok.lexeme):
            return symbol_table.get_type(tok.lexeme)
        error_handler.report("SEMANTIC", f"Undeclared variable '{tok.lexeme}' used in expression.", line)
        return None
    lt = literal_type_of(tok)
    if lt:
        return lt
    error_handler.report("SYNTAX", f"Unexpected token '{tok.lexeme}' in expression.", line)
    return None


def check_condition_is_boolean(tokens, symbol_table, error_handler, line):
    """Recursively verifies that a condition's overall type is 'bool',
    which is what C# requires inside an 'if (...)'. Handles, in order:
    && / || (splits into two sub-conditions, each must be bool),
    unary '!' (its operand must be bool),
    a relational comparison (checks both operand types are compatible),
    or a single bare operand (must itself already be of type bool,
    e.g. 'if (isReady)' where isReady was declared as bool)."""
    tokens = strip_redundant_parens(tokens)
    if not tokens:
        error_handler.report("SYNTAX", "Condition expression is empty.", line)
        return

    idx = split_top_level(tokens, {"&&", "||"})
    if idx != -1:
        check_condition_is_boolean(tokens[:idx], symbol_table, error_handler, line)
        check_condition_is_boolean(tokens[idx + 1:], symbol_table, error_handler, line)
        return

    if tokens[0].lexeme == "!":
        check_condition_is_boolean(tokens[1:], symbol_table, error_handler, line)
        return

    idx = split_top_level(tokens, {"==", "!=", "<", ">", "<=", ">="})
    if idx != -1:
        op = tokens[idx].lexeme
        left_type = get_operand_type(tokens[:idx], symbol_table, error_handler, line)
        right_type = get_operand_type(tokens[idx + 1:], symbol_table, error_handler, line)
        if left_type and right_type:
            if left_type == right_type:
                if left_type in EQUATABLE_ONLY and op not in ("==", "!="):
                    error_handler.report(
                        "SEMANTIC", f"Operator '{op}' is not defined for type '{left_type}'.", line
                    )
            elif left_type in ORDERABLE and right_type in ORDERABLE:
                pass  # numeric/char cross-comparison allowed
            else:
                error_handler.report(
                    "SEMANTIC",
                    f"Type mismatch: cannot compare type '{left_type}' with type '{right_type}' using '{op}'.",
                    line,
                )
        return

    t = get_operand_type(tokens, symbol_table, error_handler, line)
    if t and t != "bool":
        error_handler.report("SEMANTIC", f"Condition must be of type 'bool', but found type '{t}'.", line)
