"""SVG-based canvas backend for Pyodide turtle graphics.

Implements the subset of :class:`tkinter.Canvas` that the standard library
:mod:`turtle` module actually calls, rendering to an inline ``<svg>`` element
that is mounted inside an existing DOM node.

Usage example::

    from pyodide._canvas import PyodideSVGCanvas
    import turtle

    canvas = PyodideSVGCanvas("my-container", width=600, height=600)
    screen = turtle.TurtleScreen(canvas)
    pen = turtle.RawTurtle(screen)
    pen.forward(100)
"""

from __future__ import annotations

import re
from typing import Any

_SVG_NS = "http://www.w3.org/2000/svg"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# A representative set of CSS named colors — used as a fast first-pass
# validator when the DOM is not available (e.g. Node.js / unit tests).
_CSS_NAMED_COLORS: frozenset[str] = frozenset(
    [
        "aliceblue", "antiquewhite", "aqua", "aquamarine", "azure", "beige",
        "bisque", "black", "blanchedalmond", "blue", "blueviolet", "brown",
        "burlywood", "cadetblue", "chartreuse", "chocolate", "coral",
        "cornflowerblue", "cornsilk", "crimson", "cyan", "darkblue",
        "darkcyan", "darkgoldenrod", "darkgray", "darkgreen", "darkgrey",
        "darkkhaki", "darkmagenta", "darkolivegreen", "darkorange",
        "darkorchid", "darkred", "darksalmon", "darkseagreen",
        "darkslateblue", "darkslategray", "darkslategrey", "darkturquoise",
        "darkviolet", "deeppink", "deepskyblue", "dimgray", "dimgrey",
        "dodgerblue", "firebrick", "floralwhite", "forestgreen", "fuchsia",
        "gainsboro", "ghostwhite", "gold", "goldenrod", "gray", "green",
        "greenyellow", "grey", "honeydew", "hotpink", "indianred", "indigo",
        "ivory", "khaki", "lavender", "lavenderblush", "lawngreen",
        "lemonchiffon", "lightblue", "lightcoral", "lightcyan",
        "lightgoldenrodyellow", "lightgray", "lightgreen", "lightgrey",
        "lightpink", "lightsalmon", "lightseagreen", "lightskyblue",
        "lightslategray", "lightslategrey", "lightsteelblue", "lightyellow",
        "lime", "limegreen", "linen", "magenta", "maroon", "mediumaquamarine",
        "mediumblue", "mediumorchid", "mediumpurple", "mediumseagreen",
        "mediumslateblue", "mediumspringgreen", "mediumturquoise",
        "mediumvioletred", "midnightblue", "mintcream", "mistyrose",
        "moccasin", "navajowhite", "navy", "oldlace", "olive", "olivedrab",
        "orange", "orangered", "orchid", "palegoldenrod", "palegreen",
        "paleturquoise", "palevioletred", "papayawhip", "peachpuff", "peru",
        "pink", "plum", "powderblue", "purple", "red", "rosybrown",
        "royalblue", "saddlebrown", "salmon", "sandybrown", "seagreen",
        "seashell", "sienna", "silver", "skyblue", "slateblue", "slategray",
        "slategrey", "snow", "springgreen", "steelblue", "tan", "teal",
        "thistle", "tomato", "turquoise", "violet", "wheat", "white",
        "whitesmoke", "yellow", "yellowgreen",
        # special
        "transparent",
    ]
)

_HEX6_RE = re.compile(r"^#([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})$")
_HEX3_RE = re.compile(r"^#([0-9a-fA-F])([0-9a-fA-F])([0-9a-fA-F])$")
_RGB_RE = re.compile(r"^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)")


def _svg_color(color: str) -> str:
    """Convert a tkinter color value to an SVG-compatible string.

    An empty string maps to ``"none"``; everything else is passed through
    unchanged (SVG understands the same CSS colour names and hex codes that
    turtle uses).
    """
    return color if color else "none"


def _parse_rgb(normalized: str) -> tuple[int, int, int] | None:
    """Parse a browser-normalised colour string into an (r, g, b) triple."""
    m = _HEX6_RE.match(normalized)
    if m:
        return int(m.group(1), 16), int(m.group(2), 16), int(m.group(3), 16)
    m = _RGB_RE.match(normalized)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return None


# ---------------------------------------------------------------------------
# Fake Tk object — satisfies cv.tk.mainloop()
# ---------------------------------------------------------------------------


class _FakeTk:
    def mainloop(self, n: int = 0) -> None:
        pass


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class PyodideSVGCanvas:
    """SVG-backed canvas that mirrors the :class:`tkinter.Canvas` subset used
    by the standard :mod:`turtle` module.

    Parameters
    ----------
    container_id:
        ``id`` attribute of the DOM element that will host the ``<svg>``.
    width:
        Canvas width in pixels.
    height:
        Canvas height in pixels.
    """

    def __init__(
        self, container_id: str, width: int = 500, height: int = 500
    ) -> None:
        from js import document  # type: ignore[import]

        self._width = width
        self._height = height
        self._bg = "white"

        # Per-item bookkeeping
        self._items: dict[int, Any] = {}
        self._item_types: dict[int, str] = {}
        self._item_coords: dict[int, list[float]] = {}
        self._next_id = 1

        # Fake Tk root — turtle calls cv.tk.mainloop()
        self.tk = _FakeTk()

        # ----------------------------------------------------------------
        # Build the SVG tree
        # ----------------------------------------------------------------
        container = document.getElementById(container_id)
        if container is None:
            raise ValueError(f"No DOM element with id {container_id!r}")

        self._svg = document.createElementNS(_SVG_NS, "svg")
        self._svg.setAttribute("width", str(width))
        self._svg.setAttribute("height", str(height))
        self._svg.setAttribute("xmlns", _SVG_NS)
        self._svg.style.display = "block"
        # Allow the SVG to receive keyboard events
        self._svg.setAttribute("tabindex", "0")

        # Background rectangle
        self._bg_rect = document.createElementNS(_SVG_NS, "rect")
        self._bg_rect.setAttribute("x", "0")
        self._bg_rect.setAttribute("y", "0")
        self._bg_rect.setAttribute("width", str(width))
        self._bg_rect.setAttribute("height", str(height))
        self._bg_rect.setAttribute("fill", self._bg)
        self._svg.appendChild(self._bg_rect)

        # Drawing group — turtle.py negates y, so we only need to translate
        # the origin from (0,0) at top-left to the centre of the canvas.
        self._group = document.createElementNS(_SVG_NS, "g")
        self._group.setAttribute(
            "transform", f"translate({width // 2},{height // 2})"
        )
        self._svg.appendChild(self._group)

        container.appendChild(self._svg)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _alloc_id(self) -> int:
        id_ = self._next_id
        self._next_id += 1
        return id_

    def _get_element(self, item: int) -> Any | None:
        return self._items.get(item)

    # ------------------------------------------------------------------
    # Canvas configuration
    # ------------------------------------------------------------------

    def cget(self, attr: str) -> str:
        """Return canvas configuration value."""
        if attr in ("width", "canvwidth"):
            return str(self._width)
        if attr in ("height", "canvheight"):
            return str(self._height)
        if attr == "bg":
            return self._bg
        return ""

    def config(self, **kwargs: Any) -> None:
        """Configure canvas options."""
        if "bg" in kwargs:
            self._bg = kwargs["bg"]
            self._bg_rect.setAttribute("fill", self._bg)
        # scrollregion and other tkinter-only options are ignored

    # ------------------------------------------------------------------
    # Item creation
    # ------------------------------------------------------------------

    def create_line(self, *args: Any, **kwargs: Any) -> int:
        """Create a polyline item and return its id."""
        from js import document  # type: ignore[import]

        id_ = self._alloc_id()
        el = document.createElementNS(_SVG_NS, "polyline")

        # First four positional args are x0,y0,x1,y1
        coords: list[float] = list(args[:4]) if len(args) >= 4 else list(args) + [0.0] * (4 - len(args))
        points = f"{coords[0]},{coords[1]} {coords[2]},{coords[3]}"
        el.setAttribute("points", points)

        el.setAttribute("fill", "none")
        el.setAttribute("stroke", _svg_color(str(kwargs.get("fill", "black"))))
        el.setAttribute("stroke-width", str(kwargs.get("width", 1)))

        capstyle = kwargs.get("capstyle", "")
        if capstyle:
            el.setAttribute("stroke-linecap", str(capstyle).lower())

        self._group.appendChild(el)
        self._items[id_] = el
        self._item_types[id_] = "line"
        self._item_coords[id_] = coords
        return id_

    def create_polygon(self, *args: Any, **kwargs: Any) -> int:
        """Create a polygon item and return its id."""
        from js import document  # type: ignore[import]

        id_ = self._alloc_id()
        el = document.createElementNS(_SVG_NS, "polygon")

        # turtle passes coords as a single iterable or as positional args
        if len(args) == 1 and hasattr(args[0], "__iter__"):
            raw = list(args[0])
        else:
            raw = list(args)

        points = " ".join(
            f"{raw[i]},{raw[i + 1]}" for i in range(0, len(raw) - 1, 2)
        )
        el.setAttribute("points", points)
        el.setAttribute("fill", _svg_color(str(kwargs.get("fill", ""))))
        el.setAttribute("stroke", _svg_color(str(kwargs.get("outline", ""))))
        if "width" in kwargs:
            el.setAttribute("stroke-width", str(kwargs["width"]))

        self._group.appendChild(el)
        self._items[id_] = el
        self._item_types[id_] = "polygon"
        self._item_coords[id_] = raw
        return id_

    def create_oval(
        self, x0: float, y0: float, x1: float, y1: float, **kwargs: Any
    ) -> int:
        """Create an ellipse item and return its id."""
        from js import document  # type: ignore[import]

        id_ = self._alloc_id()
        el = document.createElementNS(_SVG_NS, "ellipse")

        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2
        rx = abs(x1 - x0) / 2
        ry = abs(y1 - y0) / 2

        el.setAttribute("cx", str(cx))
        el.setAttribute("cy", str(cy))
        el.setAttribute("rx", str(rx))
        el.setAttribute("ry", str(ry))
        el.setAttribute("fill", _svg_color(str(kwargs.get("fill", ""))))
        el.setAttribute("stroke", _svg_color(str(kwargs.get("outline", ""))))

        self._group.appendChild(el)
        self._items[id_] = el
        self._item_types[id_] = "oval"
        self._item_coords[id_] = [x0, y0, x1, y1]
        return id_

    def create_text(self, x: float, y: float, **kwargs: Any) -> int:
        """Create a text item and return its id."""
        from js import document  # type: ignore[import]

        id_ = self._alloc_id()
        el = document.createElementNS(_SVG_NS, "text")

        el.setAttribute("x", str(x))
        el.setAttribute("y", str(y))

        text = str(kwargs.get("text", ""))
        el.textContent = text

        anchor = kwargs.get("anchor", "center")
        _anchor_map = {
            "center": "middle",
            "nw": "start", "n": "middle", "ne": "end",
            "w": "start", "e": "end",
            "sw": "start", "s": "middle", "se": "end",
        }
        el.setAttribute("text-anchor", _anchor_map.get(str(anchor), "middle"))

        if "fill" in kwargs:
            el.setAttribute("fill", str(kwargs["fill"]))
        if "font" in kwargs:
            font = kwargs["font"]
            if isinstance(font, (list, tuple)):
                if len(font) >= 1:
                    el.setAttribute("font-family", str(font[0]))
                if len(font) >= 2:
                    el.setAttribute("font-size", str(font[1]))
                if len(font) >= 3:
                    el.setAttribute("font-style", str(font[2]))

        self._group.appendChild(el)
        self._items[id_] = el
        self._item_types[id_] = "text"
        self._item_coords[id_] = [x, y]
        return id_

    def create_image(self, x: float, y: float, **kwargs: Any) -> int:
        """Create an image item and return its id (image display not supported)."""
        from js import document  # type: ignore[import]

        id_ = self._alloc_id()
        el = document.createElementNS(_SVG_NS, "image")
        el.setAttribute("x", str(x))
        el.setAttribute("y", str(y))

        self._group.appendChild(el)
        self._items[id_] = el
        self._item_types[id_] = "image"
        self._item_coords[id_] = [x, y]
        return id_

    # ------------------------------------------------------------------
    # Item manipulation
    # ------------------------------------------------------------------

    def coords(self, item: int, *args: Any) -> list[float]:
        """Get or set the coordinates of an item."""
        if not args:
            return list(self._item_coords.get(item, []))

        flat = list(args)
        self._item_coords[item] = flat

        el = self._items.get(item)
        if el is None:
            return flat

        itype = self._item_types.get(item, "")
        if itype in ("line", "polygon"):
            points = " ".join(
                f"{flat[i]},{flat[i + 1]}" for i in range(0, len(flat) - 1, 2)
            )
            el.setAttribute("points", points)
        elif itype == "text":
            if len(flat) >= 2:
                el.setAttribute("x", str(flat[0]))
                el.setAttribute("y", str(flat[1]))
        elif itype in ("image", "oval"):
            if len(flat) >= 2:
                el.setAttribute("x", str(flat[0]))
                el.setAttribute("y", str(flat[1]))

        return flat

    def itemconfigure(self, item: int, **kwargs: Any) -> None:
        """Configure display properties of an item."""
        el = self._items.get(item)
        if el is None:
            return

        itype = self._item_types.get(item, "")

        if "fill" in kwargs:
            fill = str(kwargs["fill"])
            if itype == "line":
                # For lines, tkinter's "fill" is the stroke colour
                el.setAttribute("stroke", _svg_color(fill))
            else:
                el.setAttribute("fill", _svg_color(fill))

        if "outline" in kwargs:
            el.setAttribute("stroke", _svg_color(str(kwargs["outline"])))

        if "width" in kwargs:
            el.setAttribute("stroke-width", str(kwargs["width"]))

        if "text" in kwargs:
            el.textContent = str(kwargs["text"])

        if "state" in kwargs:
            el.setAttribute(
                "visibility",
                "hidden" if kwargs["state"] == "hidden" else "visible",
            )

    # alias used by some turtle internals
    itemconfig = itemconfigure

    def delete(self, item: Any) -> None:
        """Delete one item or all items (``"all"``)."""
        if item == "all":
            for el in list(self._items.values()):
                if el.parentNode:
                    el.parentNode.removeChild(el)
            self._items.clear()
            self._item_types.clear()
            self._item_coords.clear()
            return

        el = self._items.pop(item, None)
        if el is not None:
            if el.parentNode:
                el.parentNode.removeChild(el)
            self._item_types.pop(item, None)
            self._item_coords.pop(item, None)

    def move(self, item: int, dx: float, dy: float) -> None:
        """Translate an item by *(dx, dy)*."""
        old = self._item_coords.get(item, [])
        new: list[float] = []
        for i, v in enumerate(old):
            new.append(v + (dx if i % 2 == 0 else dy))
        self.coords(item, *new)

    def tag_raise(self, item: int, *args: Any) -> None:
        """Raise an item to the top of the stacking order."""
        el = self._items.get(item)
        if el is not None and el.parentNode:
            el.parentNode.appendChild(el)

    def tag_lower(self, item: int, *args: Any) -> None:
        """Lower an item to the bottom of the stacking order."""
        el = self._items.get(item)
        if el is not None and el.parentNode:
            parent = el.parentNode
            first = parent.firstChild
            if first is not None and first != el:
                parent.insertBefore(el, first)

    # ------------------------------------------------------------------
    # Scheduling / events
    # ------------------------------------------------------------------

    def after(self, ms: int, callback: Any = None) -> None:
        """Schedule *callback* after *ms* milliseconds.

        When *callback* is ``None`` the call is a no-op (turtle uses it as
        a yield-point; in a browser the event loop handles scheduling).
        """
        if callback is not None:
            from js import setTimeout  # type: ignore[import]

            setTimeout(callback, ms)

    def after_idle(self, callback: Any) -> None:
        """Schedule *callback* for the next idle cycle."""
        from js import setTimeout  # type: ignore[import]

        setTimeout(callback, 0)

    def bind(self, event: str, callback: Any) -> None:
        """Bind *callback* to a DOM event on the SVG element."""
        dom_event = _tk_event_to_dom(event)
        if dom_event:
            self._svg.addEventListener(dom_event, callback)

    def unbind(self, event: str, funcid: Any = None) -> None:
        """Unbind an event from the SVG element (simplified — no-op)."""

    def tag_bind(
        self, item: int, event: str, callback: Any, add: Any = None
    ) -> None:
        """Bind *callback* to *event* on a specific item."""
        el = self._items.get(item)
        if el is not None:
            dom_event = _tk_event_to_dom(event)
            if dom_event:
                el.addEventListener(dom_event, callback)

    def tag_unbind(
        self, item: int, event: str, funcid: Any = None
    ) -> None:
        """Unbind an event from a specific item (simplified — no-op)."""

    def focus_force(self) -> None:
        """Move keyboard focus to the SVG element."""
        self._svg.focus()

    # ------------------------------------------------------------------
    # Dimension / colour queries
    # ------------------------------------------------------------------

    def winfo_width(self) -> int:
        """Return canvas width in pixels."""
        return self._width

    def winfo_height(self) -> int:
        """Return canvas height in pixels."""
        return self._height

    def winfo_rgb(self, color: str) -> tuple[int, int, int]:
        """Validate *color* and return its ``(r, g, b)`` components (16-bit).

        Raises :class:`tkinter.TclError` if *color* is not recognised.
        The 16-bit range (0–65535) matches the return convention used by the
        real :func:`tkinter.Misc.winfo_rgb`.
        """
        from tkinter import TclError  # our stub raises correctly

        rgb = _resolve_color(color)
        if rgb is None:
            raise TclError(f"unknown color name '{color}'")
        r, g, b = rgb
        # tkinter returns 16-bit per channel
        return (r * 257, g * 257, b * 257)

    def winfo_toplevel(self) -> "PyodideSVGCanvas":
        """Return self — turtle only calls this on macOS (sys.platform == 'darwin')."""
        return self

    def bbox(self, item: int) -> tuple[int, int, int, int]:
        """Return the bounding box ``(x0, y0, x1, y1)`` of an item."""
        coords = self._item_coords.get(item)
        if not coords or len(coords) < 2:
            return (0, 0, 0, 0)
        xs = [coords[i] for i in range(0, len(coords), 2)]
        ys = [coords[i] for i in range(1, len(coords), 2)]
        return (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys)))

    def canvasx(self, x: float) -> float:
        """Convert window x-coordinate to canvas x-coordinate."""
        return x - self._width / 2

    def canvasy(self, y: float) -> float:
        """Convert window y-coordinate to canvas y-coordinate."""
        return y - self._height / 2

    def update(self) -> None:
        """Force a canvas redraw (no-op — the DOM updates synchronously)."""

    def type(self, item: int) -> str:
        """Return the item type string."""
        return self._item_types.get(item, "")

    def find_all(self) -> list[int]:
        """Return a list of all item ids."""
        return list(self._items.keys())


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _tk_event_to_dom(event: str) -> str:
    """Map a tkinter event specifier to a DOM event name."""
    _MAP = {
        "<Button-1>": "click",
        "<Button-2>": "auxclick",
        "<Button-3>": "contextmenu",
        "<ButtonRelease-1>": "mouseup",
        "<Button1-ButtonRelease>": "mouseup",
        "<Button1-Motion>": "mousemove",
        "<Button2-Motion>": "mousemove",
        "<Button3-Motion>": "mousemove",
        "<KeyPress>": "keydown",
        "<KeyRelease>": "keyup",
    }
    return _MAP.get(event, "")


def _resolve_color(color: str) -> tuple[int, int, int] | None:
    """Return ``(r, g, b)`` (0–255) for *color*, or ``None`` if invalid.

    Tries the browser's CSS colour parser first; falls back to a built-in
    table so that the function also works in Node.js / pure-Python tests.
    """
    # Try browser colour parser
    try:
        from js import document  # type: ignore[import]

        canvas_el = document.createElement("canvas")
        canvas_el.width = canvas_el.height = 1
        ctx = canvas_el.getContext("2d")
        # Use a sentinel that cannot occur naturally
        ctx.fillStyle = "rgb(1,2,3)"
        ctx.fillStyle = color
        normalized: str = ctx.fillStyle
        # If the browser rejected the colour it resets to the previous value
        if normalized == "rgb(1, 2, 3)":
            # Edge-case: the user literally passed the sentinel
            if color.replace(" ", "") not in ("rgb(1,2,3)", "#010203"):
                return None
        return _parse_rgb(normalized)
    except Exception:
        pass

    # Fallback: named-colour table + hex
    lc = color.strip().lower()
    if lc in _CSS_NAMED_COLORS:
        # We don't know the exact RGB for every name without a lookup table;
        # return a sentinel (0,0,0) that is only used to signal "valid".
        return (0, 0, 0)

    m = _HEX6_RE.match(color)
    if m:
        return int(m.group(1), 16), int(m.group(2), 16), int(m.group(3), 16)

    m = _HEX3_RE.match(color)
    if m:
        r = int(m.group(1) * 2, 16)
        g = int(m.group(2) * 2, 16)
        b = int(m.group(3) * 2, 16)
        return r, g, b

    m = _RGB_RE.match(color)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))

    return None
