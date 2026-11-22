"""Input helpers and table printing. Every prompt loops until it gets a valid
answer, so bad input never crashes the program."""
import getpass
import re
import sys
from datetime import datetime

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def ask(prompt, required=True, default=None):
    """Ask for text. Empty input is refused when required, or returns default."""
    while True:
        suffix = f" [{default}]" if default else ""
        value = input(f"{prompt}{suffix}: ").strip()
        if value:
            return value
        if default is not None:
            return default
        if not required:
            return ""
        print("  This field cannot be empty.")


def ask_int(prompt, low=None, high=None):
    while True:
        raw = input(f"{prompt}: ").strip()
        try:
            number = int(raw)
        except ValueError:
            print("  Please enter a whole number.")
            continue
        if (low is not None and number < low) or \
                (high is not None and number > high):
            print(f"  Enter a number between {low} and {high}."
                  if low is not None and high is not None
                  else "  That number is out of range.")
            continue
        return number


def ask_choice(prompt, options, allow_skip=False):
    """Show a numbered list and return the chosen option (or None to skip)."""
    for i, option in enumerate(options, 1):
        print(f"  {i}. {option}")
    if allow_skip:
        print("  0. Any / skip")
    while True:
        number = ask_int(prompt, 0 if allow_skip else 1, len(options))
        if number == 0 and allow_skip:
            return None
        return options[number - 1]


def ask_date(prompt):
    while True:
        raw = input(f"{prompt} (YYYY-MM-DD): ").strip()
        try:
            return datetime.strptime(raw, "%Y-%m-%d").date().isoformat()
        except ValueError:
            print("  Invalid date. Example: 2026-12-05")


def ask_yes_no(prompt):
    while True:
        answer = input(f"{prompt} (y/n): ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  Please answer y or n.")


def ask_email(prompt="Email"):
    while True:
        value = ask(prompt)
        if EMAIL_RE.match(value):
            return value
        print("  That does not look like an email address.")


def _secret(prompt):
    """Hidden input in a real terminal; plain input when piped (tests)."""
    if sys.stdin.isatty():
        return getpass.getpass(prompt)
    return input(prompt)


def ask_password(prompt="Password", confirm=False):
    while True:
        password = _secret(f"{prompt}: ")
        if confirm and len(password) < 6:
            print("  Use at least 6 characters.")
            continue
        if confirm and _secret("Repeat password: ") != password:
            print("  Passwords do not match.")
            continue
        return password


def clip(text, width):
    text = "" if text is None else str(text)
    return text if len(text) <= width else text[:width - 1] + "…"


def show_table(rows, columns):
    """columns: list of (heading, key_or_callable, width)."""
    if not rows:
        print("  (nothing to show)")
        return
    header = " | ".join(h.ljust(w) for h, _, w in columns)
    print("  " + header)
    print("  " + "-+-".join("-" * w for _, _, w in columns))
    for row in rows:
        cells = []
        for _, key, width in columns:
            value = key(row) if callable(key) else row[key]
            cells.append(clip(value, width).ljust(width))
        print("  " + " | ".join(cells))


def pause():
    input("\nPress Enter to continue...")


def banner(text):
    print("\n" + "=" * 60)
    print(f" {text}")
    print("=" * 60)


def menu(title, options):
    """Print a menu and return the chosen number (0 = last option usually)."""
    banner(title)
    for key, label in options:
        print(f"  {key}. {label}")
    valid = {str(k) for k, _ in options}
    while True:
        choice = input("Choose: ").strip()
        if choice in valid:
            return choice
        print("  Not a valid option.")
