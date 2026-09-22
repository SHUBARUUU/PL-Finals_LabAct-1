"""
main.py
-------
Interactive console entry point. Prompts the user for optional 'declare'
lines to build a symbol table, then for the C# if/switch statement to
analyze, and runs it through the Compiler facade.

Run with:  python main.py
"""

from helper_classes.compiler import Compiler


def read_declare_section():
    print("\nEnter variable declarations to build the symbol table.")
    print("Format: declare <type> <name> = <value>;   (types: int, string, bool, double, char)")
    print("Type 'end' on its own line when finished, or 'skip' if there are none.\n")
    lines = []
    
    while True:
        line = input("declare> ").strip()
        if line.lower() == "skip":
            return []
        if line.lower() == "end":
            break
        if line:
            lines.append(line)
    return lines


def read_statement_section():
    print("\nEnter your C# 'if' or 'switch' statement (it can span multiple lines).")
    print("Type 'END' (all caps) on its own line when finished.\n")
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines)


def main():
    print("=" * 70)
    print("  C# CONDITIONAL STATEMENT COMPILER (if / switch)")
    print("  Lexical - Syntax - Semantic Analyzer  (written in Python)")
    print("=" * 70)
    while True:
        choice = input("\nAnalyze a new statement? (yes/no): ").strip().lower()
        if choice in ("no", "n", "exit", "quit"):
            print("Goodbye!")
            break
        if choice not in ("yes", "y"):
            print("Please type 'yes' or 'no'.")
            continue
        declare_lines = read_declare_section()
        statement_text = read_statement_section()
        Compiler(declare_lines, statement_text).run()


if __name__ == "__main__":
    main()
