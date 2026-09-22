"""
compiler.py
-----------
Ties everything together for one test run: build the symbol table from
the 'declare' lines -> lex the statement -> print the lexeme/token
table -> parse it -> run semantic checks -> print the final verdict.

This is the "facade" that main.py talks to; it is the only module that
needs to know about every other module in the package.
"""

from .tokens import TokenType, TYPE_KEYWORDS, literal_type_of
from .error_handler import ErrorHandler
from .symbol_table import SymbolTable
from .lexer import Lexer
from .parser import Parser


class Compiler:
    def __init__(self, declare_lines, statement_text):
        self.declare_lines = declare_lines
        self.statement_text = statement_text
        self.error_handler = ErrorHandler()
        self.symbol_table = SymbolTable()

    def run(self):
        print("\n" + "=" * 70)
        print("STEP 1: SYMBOL TABLE (from 'declare' lines)")
        print("=" * 70)
        self._process_declarations()
        if not self.declare_lines:
            print("(No declarations were provided.)")

        print("\n" + "=" * 70)
        print("STEP 2: LEXICAL ANALYSIS - Lexemes and Tokens")
        print("=" * 70)
        lexer = Lexer(self.statement_text, self.error_handler)
        tokens = lexer.tokenize()
        self._print_token_table(tokens)

        print("\n" + "=" * 70)
        print("STEP 3: SYNTAX & SEMANTIC ANALYSIS")
        print("=" * 70)
        parser = Parser(tokens, self.error_handler)
        ast_node = parser.parse_program()
        if ast_node is not None:
            ast_node.check_semantics(self.symbol_table, self.error_handler)
            print(f"Recognized construct: {ast_node.describe()}")
        else:
            print("Parsing halted: the input does not begin with a recognizable 'if' or 'switch' statement.")

        print("\n" + "=" * 70)
        print("STEP 4: FINAL VERDICT")
        print("=" * 70)
        if self.error_handler.has_errors():
            print("Result: INVALID\n")
            self.error_handler.display()
        else:
            print("Result: VALID  (no syntax or semantic errors detected)")

    def _process_declarations(self):
        any_declared = False
        for line_no, raw_line in enumerate(self.declare_lines, 1):
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            any_declared = True
            temp_lexer = Lexer(raw_line, self.error_handler)
            toks = temp_lexer.tokenize()
            self._process_single_declaration(toks, line_no)
        if self.declare_lines and not any_declared:
            print("(No declarations were provided.)")
        elif self.declare_lines:
            print(f"{len(self.symbol_table)} variable(s) successfully declared.")

    def _process_single_declaration(self, toks, line_no):
        if not toks or toks[0].lexeme != "declare":
            shown = " ".join(t.lexeme for t in toks) if toks else "(empty line)"
            self.error_handler.report("SYNTAX", f"Declaration must start with 'declare'. Found: \"{shown}\"", line_no)
            return
        idx = 1
        if idx >= len(toks) or toks[idx].lexeme not in TYPE_KEYWORDS:
            found = toks[idx].lexeme if idx < len(toks) else "end of line"
            self.error_handler.report(
                "SYNTAX", f"Expected a valid type (int, string, bool, double, char) after 'declare', found '{found}'.", line_no
            )
            return
        var_type = toks[idx].lexeme
        idx += 1
        if idx >= len(toks) or toks[idx].type != TokenType.IDENTIFIER:
            found = toks[idx].lexeme if idx < len(toks) else "end of line"
            self.error_handler.report("SYNTAX", f"Expected a variable name, found '{found}'.", line_no)
            return
        var_name = toks[idx].lexeme
        idx += 1
        if idx >= len(toks) or toks[idx].lexeme != "=":
            self.error_handler.report("SYNTAX", f"Expected '=' after variable name '{var_name}'.", line_no)
            return
        idx += 1
        if idx >= len(toks):
            self.error_handler.report("SYNTAX", f"Expected a value after '=' for variable '{var_name}'.", line_no)
            return
        value_tok = toks[idx]
        idx += 1
        if value_tok.lexeme == "-" and idx < len(toks) and literal_type_of(toks[idx]) in ("int", "double"):
            value_tok = toks[idx]
            idx += 1
        if idx >= len(toks) or toks[idx].lexeme != ";":
            self.error_handler.report("SYNTAX", f"Missing ';' at the end of the declaration of '{var_name}'.", line_no)
        value_type = literal_type_of(value_tok)
        if value_type is None:
            self.error_handler.report("SYNTAX", f"Expected a literal value for '{var_name}', found '{value_tok.lexeme}'.", line_no)
        elif value_type != var_type and not (var_type == "double" and value_type == "int"):
            self.error_handler.report(
                "SEMANTIC", f"Cannot assign a value of type '{value_type}' to variable '{var_name}' of type '{var_type}'.", line_no
            )
        self.symbol_table.declare(var_name, var_type, self.error_handler, line_no)

    def _print_token_table(self, tokens):
        if not tokens:
            print("(No tokens found - the statement was empty.)")
            return
        print(f"{'No.':<5}{'Lexeme':<20}{'Token Type':<18}{'Line':<6}")
        print("-" * 49)
        for i, t in enumerate(tokens, 1):
            print(f"{i:<5}{t.lexeme:<20}{t.type.name:<18}{t.line:<6}")
