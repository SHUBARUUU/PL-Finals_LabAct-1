"""
symbol_table.py
----------------
Holds every variable introduced by a 'declare' line: name -> C# type.
The semantic checks (undeclared variable, type mismatch, etc.) all
consult this table.
"""


class SymbolTable:
    """
    ENCAPSULATION: __table is private. The only way in is declare()
    (which itself validates for duplicates), and the only ways to read it
    are is_declared()/get_type() - the raw dict is never exposed.
    """

    def __init__(self):
        self.__table = {}

    def declare(self, name, var_type, error_handler, line=None):
        """Adds a variable to the table. Reports a SEMANTIC error (instead
        of overwriting) if the name was already declared."""
        if name in self.__table:
            error_handler.report("SEMANTIC", f"Variable '{name}' is already declared.", line)
            return False
        self.__table[name] = var_type
        return True

    def is_declared(self, name):
        return name in self.__table

    def get_type(self, name):
        return self.__table.get(name)

    def __len__(self):
        return len(self.__table)
