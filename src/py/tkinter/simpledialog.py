"""Stub for tkinter.simpledialog used by the turtle module.

All dialog functions return ``None`` because there is no real display
available in the Pyodide environment.
"""


def askstring(title, prompt, **kwargs):
    """Return None — no GUI dialog available in Pyodide."""
    return None


def askfloat(title, prompt, **kwargs):
    """Return None — no GUI dialog available in Pyodide."""
    return None


def askinteger(title, prompt, **kwargs):
    """Return None — no GUI dialog available in Pyodide."""
    return None
