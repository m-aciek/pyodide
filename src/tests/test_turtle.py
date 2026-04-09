"""Tests for Pyodide turtle graphics support.

Task 1 (fake tkinter) — the import must succeed without a real display.
Task 2 (PyodideSVGCanvas) — the SVG canvas backend must render to the DOM.
"""

import pytest


# ---------------------------------------------------------------------------
# Task 1 — import turtle after stubbing tkinter
# ---------------------------------------------------------------------------


def test_fake_tkinter_importable():
    """tkinter (stub) must be importable as a package."""
    import tkinter  # noqa: F401
    from tkinter import simpledialog  # noqa: F401


def test_turtle_import_succeeds():
    """import turtle must succeed when the tkinter stub is present."""
    import turtle  # noqa: F401


def test_turtle_core_api_available():
    """Key public names from the turtle module must be importable."""
    import turtle

    assert callable(turtle.forward)
    assert callable(turtle.backward)
    assert callable(turtle.left)
    assert callable(turtle.right)
    assert callable(turtle.penup)
    assert callable(turtle.pendown)


def test_turtle_turtlescreen_with_fake_canvas():
    """TurtleScreen must accept a minimal fake canvas without errors."""
    import turtle
    import tkinter as TK

    canvas = TK.Canvas()
    screen = turtle.TurtleScreen(canvas)
    assert screen is not None


# ---------------------------------------------------------------------------
# Task 2 — PyodideSVGCanvas unit tests (no DOM required)
# ---------------------------------------------------------------------------


def test_pyodide_svg_canvas_importable():
    """PyodideSVGCanvas must be importable from pyodide._canvas."""
    from pyodide._canvas import PyodideSVGCanvas  # noqa: F401


def test_resolve_color_named():
    """Named CSS colours must resolve to a non-None RGB triple."""
    from pyodide._canvas import _resolve_color

    assert _resolve_color("red") is not None
    assert _resolve_color("black") is not None
    assert _resolve_color("white") is not None


def test_resolve_color_hex6():
    """Six-digit hex colours must parse correctly."""
    from pyodide._canvas import _resolve_color

    result = _resolve_color("#ff0000")
    assert result == (255, 0, 0)


def test_resolve_color_hex3():
    """Three-digit hex colours must expand and parse correctly."""
    from pyodide._canvas import _resolve_color

    result = _resolve_color("#f00")
    assert result == (255, 0, 0)


def test_resolve_color_rgb_func():
    """rgb() colour strings must parse correctly."""
    from pyodide._canvas import _resolve_color

    result = _resolve_color("rgb(10,20,30)")
    assert result == (10, 20, 30)


def test_resolve_color_invalid():
    """Unrecognised colour strings must return None."""
    from pyodide._canvas import _resolve_color

    assert _resolve_color("notacolor_xyz") is None
    assert _resolve_color("##gg0000") is None


def test_svg_color_empty():
    """An empty colour string must map to 'none' in SVG."""
    from pyodide._canvas import _svg_color

    assert _svg_color("") == "none"
    assert _svg_color("red") == "red"


def test_tk_event_to_dom_mapping():
    """Common tkinter event strings must map to their DOM equivalents."""
    from pyodide._canvas import _tk_event_to_dom

    assert _tk_event_to_dom("<Button-1>") == "click"
    assert _tk_event_to_dom("<KeyPress>") == "keydown"
    assert _tk_event_to_dom("<Button1-Motion>") == "mousemove"
    assert _tk_event_to_dom("<UnknownEvent>") == ""


# ---------------------------------------------------------------------------
# Task 2 — PyodideSVGCanvas DOM tests (browser only)
# ---------------------------------------------------------------------------


@pytest.mark.xfail_browsers(node="No document object in Node.js")
def test_svg_canvas_mounts_to_dom(selenium_standalone_refresh):
    """PyodideSVGCanvas must create an <svg> element inside the container."""
    selenium_standalone_refresh.run_js(
        """
        const div = document.createElement("div");
        div.id = "turtle-test-container";
        document.body.appendChild(div);

        await pyodide.runPythonAsync(`
            from pyodide._canvas import PyodideSVGCanvas
            canvas = PyodideSVGCanvas("turtle-test-container", width=400, height=400)
            assert canvas.winfo_width() == 400
            assert canvas.winfo_height() == 400
        `);

        const svg = div.querySelector("svg");
        assert(() => svg !== null);
        assert(() => svg.getAttribute("width") === "400");
        """
    )


@pytest.mark.xfail_browsers(node="No document object in Node.js")
def test_svg_canvas_basic_drawing(selenium_standalone_refresh):
    """Basic turtle drawing must create SVG elements in the DOM."""
    selenium_standalone_refresh.run_js(
        """
        const div = document.createElement("div");
        div.id = "turtle-draw-container";
        document.body.appendChild(div);

        await pyodide.runPythonAsync(`
            import turtle
            from pyodide._canvas import PyodideSVGCanvas

            canvas = PyodideSVGCanvas("turtle-draw-container", width=400, height=400)
            screen = turtle.TurtleScreen(canvas)
            pen = turtle.RawTurtle(screen)
            pen.speed(0)
            pen.forward(50)
            pen.left(90)
            pen.forward(50)
        `);

        const polylines = div.querySelectorAll("polyline");
        assert(() => polylines.length > 0, "Expected at least one polyline element");
        """
    )


@pytest.mark.xfail_browsers(node="No document object in Node.js")
def test_svg_canvas_bgcolor(selenium_standalone_refresh):
    """Setting the background colour must update the SVG background rect."""
    selenium_standalone_refresh.run_js(
        """
        const div = document.createElement("div");
        div.id = "turtle-bg-container";
        document.body.appendChild(div);

        await pyodide.runPythonAsync(`
            import turtle
            from pyodide._canvas import PyodideSVGCanvas

            canvas = PyodideSVGCanvas("turtle-bg-container", width=300, height=300)
            canvas.config(bg="lightblue")
            assert canvas.cget("bg") == "lightblue"
        `);

        const rect = div.querySelector("rect");
        assert(() => rect.getAttribute("fill") === "lightblue");
        """
    )
