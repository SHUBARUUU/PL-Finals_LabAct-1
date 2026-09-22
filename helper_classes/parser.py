"""
parser.py
---------
Reads the token list produced by the Lexer and builds an IfStatement or
SwitchStatement object out of it (checking the *structure* - syntax -
along the way). Error recovery here is intentionally simple: when an
expected token is missing, we log the error and keep parsing from where
we are instead of stopping, so that one mistake doesn't hide every
other error in the same statement (this is why a single bad input can
report several related errors at once, e.g. a missing '{' cascading
into a "missing '}'" error too).
"""

from .statements import IfStatement, SwitchStatement, CaseClause, SimpleStatement


class Parser:
    def __init__(self, tokens, error_handler):
        self.tokens = tokens
        self.pos = 0
        self.error_handler = error_handler

    def _peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _advance(self):
        t = self._peek()
        self.pos += 1
        return t

    def _check(self, lexeme):
        t = self._peek()
        return t is not None and t.lexeme == lexeme

    def _expect(self, lexeme, context=""):
        t = self._peek()
        if t is not None and t.lexeme == lexeme:
            return self._advance()
        line = t.line if t else (self.tokens[-1].line if self.tokens else 1)
        found = t.lexeme if t else "end of input"
        suffix = f" {context}" if context else ""
        self.error_handler.report("SYNTAX", f"Expected '{lexeme}'{suffix} but found '{found}'.", line)
        return None

    def parse_program(self):
        """Entry point: a valid program here is exactly one 'if' or one
        'switch' statement - anything else is a syntax error."""
        t = self._peek()
        if t is None:
            self.error_handler.report("SYNTAX", "No input provided.", 1)
            return None
        if t.lexeme == "if":
            return self.parse_if()
        if t.lexeme == "switch":
            return self.parse_switch()
        self.error_handler.report("SYNTAX", f"Expected 'if' or 'switch' statement, but found '{t.lexeme}'.", t.line)
        return None

    def _collect_parenthesized(self, opening_line):
        """Assumes the opening '(' has already been consumed."""
        tokens = []
        depth = 1
        while True:
            t = self._peek()
            if t is None:
                self.error_handler.report("SYNTAX", "Unbalanced parentheses: missing ')'.", opening_line)
                break
            if t.lexeme == "(":
                depth += 1
                tokens.append(self._advance())
            elif t.lexeme == ")":
                depth -= 1
                self._advance()
                if depth == 0:
                    break
                tokens.append(t)
            else:
                tokens.append(self._advance())
        return tokens

    def parse_if(self):
        """Grammar: 'if' '(' condition ')' block [ 'else' (if | block) ]"""
        if_tok = self._advance()
        line = if_tok.line
        self._expect("(", "after 'if'")
        condition_tokens = self._collect_parenthesized(line)
        self._expect("{", "to start the if-body")
        then_body = self.parse_block()
        else_body = None
        if self._check("else"):
            self._advance()
            if self._check("if"):
                else_body = [self.parse_if()]
            else:
                self._expect("{", "to start the else-body")
                else_body = self.parse_block()
        return IfStatement(condition_tokens, then_body, else_body, line)

    def parse_block(self):
        """Reads statements between '{' and '}'. A nested 'if'/'switch'
        is parsed recursively into its own Statement object; anything
        else is collected as an opaque SimpleStatement up to its ';'."""
        body = []
        guard = 0
        while True:
            guard += 1
            if guard > 5000:
                break
            t = self._peek()
            if t is None:
                self.error_handler.report("SYNTAX", "Unbalanced braces: missing '}'.", body[-1].line if body else 1)
                break
            if t.lexeme == "}":
                self._advance()
                break
            if t.lexeme == "if":
                body.append(self.parse_if())
            elif t.lexeme == "switch":
                body.append(self.parse_switch())
            else:
                body.append(self.parse_simple_statement())
        return body

    def parse_simple_statement(self):
        tokens = []
        start_line = self._peek().line if self._peek() else 1
        depth = 0
        while True:
            t = self._peek()
            if t is None:
                self.error_handler.report("SYNTAX", "Missing ';' to terminate statement.", tokens[-1].line if tokens else start_line)
                break
            if t.lexeme == "(":
                depth += 1
            elif t.lexeme == ")":
                depth -= 1
            elif t.lexeme == "}" and depth == 0:
                self.error_handler.report("SYNTAX", "Missing ';' to terminate statement.", t.line)
                break
            elif t.lexeme == ";" and depth == 0:
                tokens.append(self._advance())
                break
            tokens.append(self._advance())
        return SimpleStatement(tokens, start_line)

    def parse_switch(self):
        """Grammar: 'switch' '(' expr ')' '{' { case-or-default }* '}' """
        sw_tok = self._advance()
        line = sw_tok.line
        self._expect("(", "after 'switch'")
        expr_tokens = self._collect_parenthesized(line)
        switch_expr_token = None
        if len(expr_tokens) == 1:
            switch_expr_token = expr_tokens[0]
        elif len(expr_tokens) == 0:
            self.error_handler.report("SYNTAX", "Switch expression is empty.", line)
        else:
            shown = " ".join(t.lexeme for t in expr_tokens)
            self.error_handler.report(
                "SYNTAX",
                f"Unsupported switch expression '{shown}'; only a single identifier or literal is supported.",
                line,
            )
            switch_expr_token = expr_tokens[0]
        self._expect("{", "to start the switch body")

        cases = []
        guard = 0
        while True:
            guard += 1
            if guard > 2000:
                break
            t = self._peek()
            if t is None:
                self.error_handler.report("SYNTAX", "Unbalanced braces: missing '}' to close switch statement.", line)
                break
            if t.lexeme == "}":
                self._advance()
                break
            if t.lexeme == "case":
                case_line = t.line
                self._advance()
                value_tok = self._peek()
                if value_tok is not None and value_tok.lexeme != ":":
                    self._advance()
                else:
                    self.error_handler.report("SYNTAX", "Missing case value after 'case'.", case_line)
                    value_tok = None
                self._expect(":", "after the case value")
                body = self.collect_case_body()
                cases.append(CaseClause(value_tok, body, case_line, is_default=False))
            elif t.lexeme == "default":
                case_line = t.line
                self._advance()
                self._expect(":", "after 'default'")
                body = self.collect_case_body()
                cases.append(CaseClause(None, body, case_line, is_default=True))
            else:
                self.error_handler.report(
                    "SYNTAX", f"Unexpected token '{t.lexeme}' inside switch body; expected 'case', 'default', or '}}'.", t.line
                )
                self._advance()

        if not cases:
            self.error_handler.report("SEMANTIC", "Switch statement contains no 'case' or 'default' labels.", line)
        return SwitchStatement(switch_expr_token, cases, line)

    def collect_case_body(self):
        body = []
        guard = 0
        while True:
            guard += 1
            if guard > 3000:
                break
            t = self._peek()
            if t is None:
                self.error_handler.report("SYNTAX", "Unbalanced braces: missing '}' to close switch statement.", body[-1].line if body else 1)
                break
            if t.lexeme in ("case", "default", "}"):
                break
            if t.lexeme == "if":
                body.append(self.parse_if())
            elif t.lexeme == "switch":
                body.append(self.parse_switch())
            else:
                body.append(self.parse_simple_statement())
        return body
