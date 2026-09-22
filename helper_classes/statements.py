"""
statements.py
-------------
After the Parser recognizes an 'if' or 'switch', it builds one of these
objects to represent it. check_semantics() is where each construct's
own rules (bool condition for if; matching case types, no duplicate
labels, mandatory break for switch) actually get checked.

OOP requirements implemented here:
    - Abstraction   : Statement (ABC) exposes check_semantics()/describe()
                       without exposing how each construct is analyzed.
    - Inheritance   : IfStatement and SwitchStatement inherit from Statement.
    - Polymorphism  : callers (see compiler.py and the recursive body-checking
                       loops below) call check_semantics()/describe() on
                       an object they only know as "a Statement" - the
                       correct overridden version runs automatically.
"""

from abc import ABC, abstractmethod

from .tokens import literal_type_of
from .expression_utils import check_condition_is_boolean, get_operand_type


class Statement(ABC):
    """
    ABSTRACTION: this abstract base class defines *what* every recognized
    control structure must be able to do (be semantically checked, be
    described) without saying *how* - each subclass fills that in its own
    way. Code elsewhere (see Compiler.run() and the recursive body-checking
    loops) only ever talks to a plain 'Statement' and never needs to know
    or ask which concrete subclass it is holding.
    """

    def __init__(self, line):
        self._line = line

    @abstractmethod
    def check_semantics(self, symbol_table, error_handler):
        """Subclasses must implement: run this construct's semantic
        rules, reporting any problems to error_handler."""
        raise NotImplementedError

    @abstractmethod
    def describe(self):
        """Subclasses must implement: a short human-readable label."""
        raise NotImplementedError


class SimpleStatement:
    """
    An opaque, unparsed body statement, e.g. 'Console.WriteLine("hi");'.
    Deliberately NOT a Statement subclass - the lab only asks us to
    validate 'if' and 'switch' themselves, so anything else inside a
    block is kept only as raw tokens. The one thing we still need from
    it is whether it's a 'break'/'return', for the switch fall-through
    check below.
    """

    def __init__(self, tokens, line):
        self.tokens = tokens
        self.line = line

    def is_break_or_return(self):
        return len(self.tokens) >= 1 and self.tokens[0].lexeme in ("break", "return")


class IfStatement(Statement):
    """
    INHERITANCE: IfStatement IS-A Statement, and provides its own
    version of check_semantics()/describe() (POLYMORPHISM - when the
    caller invokes stmt.check_semantics(...) on this object, this
    version runs, even though the caller only knows it as a 'Statement').
    """

    def __init__(self, condition_tokens, then_body, else_body, line):
        super().__init__(line)
        self.condition_tokens = condition_tokens
        self.then_body = then_body
        self.else_body = else_body  # list or None

    def check_semantics(self, symbol_table, error_handler):
        # Rule for 'if': the condition must evaluate to type bool.
        check_condition_is_boolean(self.condition_tokens, symbol_table, error_handler, self._line)
        # Any nested if/switch inside the { } bodies gets checked too -
        # this call doesn't care whether 'stmt' is an IfStatement or a
        # SwitchStatement (that's polymorphism in action).
        for stmt in self.then_body:
            if isinstance(stmt, Statement):
                stmt.check_semantics(symbol_table, error_handler)
        if self.else_body:
            for stmt in self.else_body:
                if isinstance(stmt, Statement):
                    stmt.check_semantics(symbol_table, error_handler)

    def describe(self):
        return f"if-statement (line {self._line})"


class CaseClause:
    """Plain data holder for one 'case <value>:' or 'default:' section of
    a switch statement (not a Statement subclass itself - it's a part of
    a SwitchStatement, not a control structure on its own)."""

    def __init__(self, value_token, body, line, is_default=False):
        self.value_token = value_token
        self.body = body
        self.line = line
        self.is_default = is_default

    def has_terminator(self):
        """True if this case/default ends in break/return, OR is
        intentionally empty (stacked labels like 'case 1: case 2: ...'
        are valid C# and don't need their own break)."""
        if not self.body:
            return True
        return any(isinstance(s, SimpleStatement) and s.is_break_or_return() for s in self.body)


class SwitchStatement(Statement):
    """
    INHERITANCE + POLYMORPHISM: like IfStatement, this IS-A Statement
    with its own check_semantics()/describe(), which is a completely
    different set of rules from IfStatement's - governing type, matching
    case types, no duplicate labels, mandatory break/return per case.
    """

    ALLOWED_GOVERNING_TYPES = {"int", "string", "char", "bool"}

    def __init__(self, switch_expr_token, cases, line):
        super().__init__(line)
        self.switch_expr_token = switch_expr_token
        self.cases = cases

    def check_semantics(self, symbol_table, error_handler):
        gov_type = None
        if self.switch_expr_token is not None:
            gov_type = get_operand_type([self.switch_expr_token], symbol_table, error_handler, self._line)
            if gov_type and gov_type not in self.ALLOWED_GOVERNING_TYPES:
                error_handler.report(
                    "SEMANTIC",
                    f"Type '{gov_type}' cannot be used as a switch expression type.",
                    self._line,
                )

        seen_values = set()
        default_count = 0
        for clause in self.cases:
            if clause.is_default:
                default_count += 1
                if default_count > 1:
                    error_handler.report("SEMANTIC", "Multiple 'default' labels found in switch statement.", clause.line)
            else:
                val_tok = clause.value_token
                if val_tok is not None:
                    case_type = literal_type_of(val_tok)
                    if case_type is None:
                        error_handler.report(
                            "SYNTAX", f"Case label must be a constant literal, found '{val_tok.lexeme}'.", clause.line
                        )
                    elif gov_type and case_type != gov_type:
                        error_handler.report(
                            "SEMANTIC",
                            f"Case label '{val_tok.lexeme}' of type '{case_type}' does not match switch expression type '{gov_type}'.",
                            clause.line,
                        )
                    if val_tok.lexeme in seen_values:
                        error_handler.report("SEMANTIC", f"Duplicate case label '{val_tok.lexeme}'.", clause.line)
                    else:
                        seen_values.add(val_tok.lexeme)

            if not clause.has_terminator():
                label = "default" if clause.is_default else f"case {clause.value_token.lexeme if clause.value_token else '?'}"
                error_handler.report(
                    "SEMANTIC",
                    f"Missing 'break' or 'return' in '{label}': fall-through is not allowed in C#.",
                    clause.line,
                )

            for stmt in clause.body:
                if isinstance(stmt, Statement):
                    stmt.check_semantics(symbol_table, error_handler)  # polymorphic call

    def describe(self):
        return f"switch-statement (line {self._line})"
