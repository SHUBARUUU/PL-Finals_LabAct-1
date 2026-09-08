"""
error_handler.py
-----------------
Every single error path in this program (lexer, parser, and semantic
checks) funnels through ErrorHandler.report(). Nothing is ever printed
ad hoc or swallowed silently - this is the "error-handling method" the
lab activity calls for.
"""


class ErrorHandler:
    """
    Collects every syntax/semantic error found during analysis.

    ENCAPSULATION: __errors is a private list. Callers cannot append to it
    or read it directly - they must go through report() to add an error,
    or get_errors()/display() to read them back (get_errors() returns a
    *copy*, so the internal list still can't be mutated from outside).
    """

    VALID_CATEGORIES = {"SYNTAX", "SEMANTIC"}  # the two categories the lab requires

    def __init__(self):
        self.__errors = []

    def report(self, category, message, line=None):
        """Call this the moment any error is detected, anywhere in the
        program. category must be 'SYNTAX' or 'SEMANTIC'."""
        if category not in self.VALID_CATEGORIES:
            category = "SYNTAX"
        self.__errors.append({"category": category, "message": message, "line": line})

    def has_errors(self):
        return len(self.__errors) > 0

    def get_errors(self):
        return list(self.__errors)  # return a copy, never the private list itself

    def display(self):
        if not self.__errors:
            print("No errors detected.")
            return
        print(f"Total errors found: {len(self.__errors)}\n")
        for i, err in enumerate(self.__errors, 1):
            where = f" (line {err['line']})" if err["line"] is not None else ""
            print(f"{i}. [{err['category']} ERROR]{where}: {err['message']}")
