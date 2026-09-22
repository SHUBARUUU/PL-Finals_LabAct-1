"""
lexer.py
--------
Turns raw source text into a flat list of Token objects, one
character-scan at a time (a classic hand-written "maximal munch"
scanner: at each position it reads as many characters as possible that
still form one valid lexeme, e.g. '=' then '=' becomes the single
token '==' rather than two separate '=' tokens).
"""

from .tokens import Token, TokenType, KEYWORDS


class Lexer:
    """Converts a string of C# source into a list of Token objects,
    reporting a SYNTAX error for any character it cannot recognize."""

    SINGLE_PUNCT = set("(){};:,.")

    def __init__(self, source, error_handler):
        self.source = source
        self.error_handler = error_handler
        self.pos = 0
        self.line = 1
        self.length = len(source)

    def _peek(self, offset=0):
        idx = self.pos + offset
        return self.source[idx] if idx < self.length else ""

    def _advance(self):
        c = self.source[self.pos]
        self.pos += 1
        if c == "\n":
            self.line += 1
        return c

    def tokenize(self):
        """Main scanning loop: dispatches to the right _read_* helper
        based on the current character, one token at a time, until the
        whole source string is consumed."""
        tokens = []
        while self.pos < self.length:
            c = self._peek()
            if c in " \t\r\n":
                self._advance()
                continue
            start_line = self.line
            if c.isalpha() or c == "_":
                tokens.append(self._read_identifier(start_line))
            elif c.isdigit():
                tokens.append(self._read_number(start_line))
            elif c == '"':
                tokens.append(self._read_string(start_line))
            elif c == "'":
                tokens.append(self._read_char(start_line))
            elif c in "=!<>&|":
                tokens.append(self._read_operator(start_line))
            elif c in "+-*/%":
                self._advance()
                tokens.append(Token(TokenType.ARITH_OP, c, start_line))
            elif c in self.SINGLE_PUNCT:
                self._advance()
                tokens.append(Token(TokenType.PUNCT, c, start_line))
            else:
                # Any character that doesn't match a known pattern (e.g. @, #, $)
                # is a lexical/syntax problem - report it immediately, but still
                # emit a token so the rest of the line can still be scanned.
                self._advance()
                self.error_handler.report("SYNTAX", f"Unrecognized character '{c}'.", start_line)
                tokens.append(Token(TokenType.UNKNOWN, c, start_line))
        return tokens

    def _read_identifier(self, line):
        """Reads a run of letters/digits/underscore starting with a
        letter or underscore, then classifies it as a bool literal
        (true/false), a reserved keyword, or a plain identifier."""
        start = self.pos
        while self.pos < self.length and (self._peek().isalnum() or self._peek() == "_"):
            self._advance()
        word = self.source[start:self.pos]
        if word in ("true", "false"):
            return Token(TokenType.BOOL_LITERAL, word, line)
        if word in KEYWORDS:
            return Token(TokenType.KEYWORD, word, line)
        return Token(TokenType.IDENTIFIER, word, line)

    def _read_number(self, line):
        start = self.pos
        is_float = False
        while self.pos < self.length and self._peek().isdigit():
            self._advance()
        if self._peek() == "." and self._peek(1).isdigit():
            is_float = True
            self._advance()
            while self.pos < self.length and self._peek().isdigit():
                self._advance()
        word = self.source[start:self.pos]
        return Token(TokenType.FLOAT_LITERAL if is_float else TokenType.INT_LITERAL, word, line)

    def _read_string(self, line):
        self._advance()  # opening quote
        chars = ['"']
        terminated = False
        while self.pos < self.length:
            c = self._peek()
            if c == '"':
                self._advance()
                chars.append('"')
                terminated = True
                break
            if c == "\n":
                break
            chars.append(self._advance())
        if not terminated:
            self.error_handler.report("SYNTAX", "Unterminated string literal.", line)
        return Token(TokenType.STRING_LITERAL, "".join(chars), line)

    def _read_char(self, line):
        self._advance()  # opening quote
        chars = ["'"]
        terminated = False
        count = 0
        while self.pos < self.length:
            c = self._peek()
            if c == "'":
                self._advance()
                chars.append("'")
                terminated = True
                break
            if c == "\n":
                break
            chars.append(self._advance())
            count += 1
        if not terminated:
            self.error_handler.report("SYNTAX", "Unterminated character literal.", line)
        elif count != 1:
            self.error_handler.report("SYNTAX", "A char literal must contain exactly one character.", line)
        return Token(TokenType.CHAR_LITERAL, "".join(chars), line)

    def _read_operator(self, line):
        c = self._advance()
        two = c + self._peek()
        if two in ("==", "!=", "<=", ">=", "&&", "||"):
            self._advance()
            op_type = TokenType.RELATIONAL_OP if two in ("==", "!=", "<=", ">=") else TokenType.LOGICAL_OP
            return Token(op_type, two, line)
        if c == "=":
            return Token(TokenType.ASSIGN_OP, c, line)
        if c in ("<", ">"):
            return Token(TokenType.RELATIONAL_OP, c, line)
        if c == "!":
            return Token(TokenType.LOGICAL_OP, c, line)
        self.error_handler.report("SYNTAX", f"Unrecognized operator '{c}'. Did you mean '{c}{c}'?", line)
        return Token(TokenType.UNKNOWN, c, line)
