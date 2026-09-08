"""
tokens.py
---------
Defines what a "lexeme" and a "token" are for this compiler, and the
Token class itself.

    - A "lexeme" is the raw text the user typed (e.g. the characters "if").
    - A "token"  is the category the lexer assigns to that lexeme
      (e.g. KEYWORD).

TokenType is the fixed list of categories our lexer can produce.
"""

from enum import Enum, auto


class TokenType(Enum):
    KEYWORD = auto()         # reserved words: if, else, switch, case, default,
                              # break, return, declare, int, string, bool,
                              # double, char
    IDENTIFIER = auto()      # variable/method names, e.g. x, Console, WriteLine
    INT_LITERAL = auto()     # whole numbers, e.g. 5, 100
    FLOAT_LITERAL = auto()   # decimal numbers, e.g. 3.14 (maps to C# 'double')
    STRING_LITERAL = auto()  # "..."
    CHAR_LITERAL = auto()    # '.'
    BOOL_LITERAL = auto()    # true / false
    RELATIONAL_OP = auto()   # == != < > <= >=
    LOGICAL_OP = auto()      # && || !
    ASSIGN_OP = auto()       # =
    ARITH_OP = auto()        # + - * / %
    PUNCT = auto()           # ( ) { } ; : , .
    UNKNOWN = auto()         # any character the lexer does not recognize
                              # (this is always a reported error, never silently ignored)


KEYWORDS = {
    "declare", "if", "else", "switch", "case", "default", "break", "return",
    "int", "string", "bool", "double", "char",
}
# Subset of KEYWORDS that are valid types in a 'declare' line.
TYPE_KEYWORDS = {"int", "string", "bool", "double", "char"}


class Token:
    """
    Represents one lexeme + its token type + the source line it came from.

    ENCAPSULATION: the three fields are name-mangled private attributes
    (__type/__lexeme/__line). Outside code cannot reassign them; it can only
    *read* them through the @property getters below. This protects a Token
    from being silently corrupted after the lexer creates it.
    """

    def __init__(self, token_type, lexeme, line):
        self.__type = token_type
        self.__lexeme = lexeme
        self.__line = line

    @property
    def type(self):
        return self.__type

    @property
    def lexeme(self):
        return self.__lexeme

    @property
    def line(self):
        return self.__line

    def __repr__(self):
        return f"Token({self.__type.name}, {self.__lexeme!r}, line={self.__line})"


def literal_type_of(token):
    """Maps a literal token (e.g. INT_LITERAL) to its C# type name
    ('int'), so the semantic checks below can compare it against a
    variable's declared type. Returns None if the token is not a literal
    at all (e.g. it's an identifier or an operator)."""
    mapping = {
        TokenType.INT_LITERAL: "int",
        TokenType.FLOAT_LITERAL: "double",
        TokenType.STRING_LITERAL: "string",
        TokenType.CHAR_LITERAL: "char",
        TokenType.BOOL_LITERAL: "bool",
    }
    return mapping.get(token.type)
