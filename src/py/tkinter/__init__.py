"""Minimal tkinter stub for Pyodide.

Provides just enough of the tkinter API for the standard library ``turtle``
module to import and operate without a real display.  Only the constants,
classes, and exceptions that turtle.py actually references are implemented.
Everything else silently accepts any arguments and returns harmless defaults.
"""

# ---------------------------------------------------------------------------
# Constants used by turtle.py
# ---------------------------------------------------------------------------
ROUND = "round"
SUNKEN = "sunken"
HORIZONTAL = "horizontal"
VERTICAL = "vertical"
YES = "yes"
NO = "no"
BOTH = "both"
LAST = "last"
FIRST = "first"
NONE = "none"
NW = "nw"
N = "n"
NE = "ne"
W = "w"
CENTER = "center"
E = "e"
SW = "sw"
S = "s"
SE = "se"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TclError(Exception):
    """Stub for tkinter.TclError."""


# ---------------------------------------------------------------------------
# Base widget stub — accepts and ignores all constructor arguments
# ---------------------------------------------------------------------------


class _StubWidget:
    def __init__(self, *args, **kwargs):
        pass

    def pack(self, **kwargs):
        pass

    def grid(self, **kwargs):
        pass

    def configure(self, **kwargs):
        pass

    config = configure

    def cget(self, key):
        if key == "width":
            return "500"
        if key == "height":
            return "500"
        return ""

    def bind(self, event, callback=None, add=None):
        pass

    def unbind(self, event, funcid=None):
        pass

    def focus_force(self):
        pass

    def winfo_width(self):
        return 500

    def winfo_height(self):
        return 500

    def winfo_screenwidth(self):
        return 800

    def winfo_screenheight(self):
        return 600

    def winfo_toplevel(self):
        return self

    def winfo_rgb(self, color):
        return (0, 0, 0)

    def after(self, ms, func=None, *args):
        pass

    def after_idle(self, func, *args):
        pass


# ---------------------------------------------------------------------------
# Specific widget stubs
# ---------------------------------------------------------------------------


class Canvas(_StubWidget):
    """Stub for tkinter.Canvas — no-op drawing operations."""

    def create_line(self, *args, **kwargs):
        return 0

    def create_polygon(self, *args, **kwargs):
        return 0

    def create_text(self, *args, **kwargs):
        return 0

    def create_image(self, *args, **kwargs):
        return 0

    def create_oval(self, *args, **kwargs):
        return 0

    def coords(self, item, *args):
        return []

    def itemconfigure(self, item, **kwargs):
        pass

    itemconfig = itemconfigure

    def delete(self, *args):
        pass

    def tag_raise(self, item, *args):
        pass

    def tag_lower(self, item, *args):
        pass

    def tag_bind(self, item, event, callback, add=None):
        pass

    def tag_unbind(self, item, event, funcid=None):
        pass

    def bbox(self, *args):
        return (0, 0, 0, 0)

    def canvasx(self, x):
        return x

    def canvasy(self, y):
        return y

    def update(self):
        pass

    def type(self, item):
        return "line"

    def find_all(self):
        return []

    def xview_moveto(self, fraction):
        pass

    def yview_moveto(self, fraction):
        pass


class Frame(_StubWidget):
    """Stub for tkinter.Frame."""


class Scrollbar(_StubWidget):
    """Stub for tkinter.Scrollbar."""


class StringVar:
    """Stub for tkinter.StringVar."""

    def __init__(self, master=None, value=None, name=None):
        self._value = value or ""

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class PhotoImage:
    """Stub for tkinter.PhotoImage."""

    def __init__(self, **kwargs):
        self.width_val = int(kwargs.get("width", 1))
        self.height_val = int(kwargs.get("height", 1))

    def blank(self):
        pass

    def width(self):
        return self.width_val

    def height(self):
        return self.height_val


class _FakeTk:
    """Fake Tk-like object that satisfies ``cv.tk.mainloop()``."""

    def mainloop(self, n=0):
        pass


class Tk(_StubWidget, _FakeTk):
    """Stub for tkinter.Tk root window."""

    def __init__(self):
        self.tk = self

    def title(self, s=None):
        pass

    def ondestroy(self, fun):
        pass

    def wm_title(self, title=None):
        pass

    def wm_protocol(self, name, func=None):
        pass

    def call(self, *args):
        pass
