from __future__ import annotations

import os
import sys

try:
    from orket_extension_sdk.tui import Panel, TerminalSize
except ImportError:
    Panel = None  # type: ignore[assignment,misc]
    TerminalSize = None  # type: ignore[assignment,misc]


def _enable_windows_ansi() -> None:
    """Enable ANSI escape processing on Windows and set UTF-8 output."""
    if sys.platform != "win32":
        return
    # Enable virtual terminal processing for ANSI escapes
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        STD_OUTPUT_HANDLE = -11
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
    except Exception:
        pass
    # Set UTF-8 output encoding
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


# Box-drawing characters
_TL = "\u250c"  # top-left corner
_TR = "\u2510"  # top-right corner
_BL = "\u2514"  # bottom-left corner
_BR = "\u2518"  # bottom-right corner
_H = "\u2500"   # horizontal line
_V = "\u2502"   # vertical line


class AnsiScreenRenderer:
    """Terminal renderer using ANSI escape codes and Unicode box drawing.

    Implements orket_extension_sdk.tui.ScreenRenderer protocol.
    Zero dependencies beyond the standard library.
    """

    def __init__(self) -> None:
        _enable_windows_ansi()

    def render(self, panels: list[Panel]) -> None:
        out = sys.stdout
        for panel in panels:
            lines = panel.content.split("\n")
            content_width = max((len(line) for line in lines), default=0) + 2
            if panel.title:
                content_width = max(content_width, len(panel.title) + 4)
            width = panel.width if panel.width > 0 else content_width
            inner = width - 2

            # Top border
            if panel.title:
                title_seg = f"{_H} {panel.title} "
                remaining = max(0, inner - len(title_seg))
                out.write(f"{_TL}{title_seg}{_H * remaining}{_TR}\n")
            else:
                out.write(f"{_TL}{_H * inner}{_TR}\n")

            # Content lines
            for line in lines:
                padded = line[:inner].ljust(inner)
                out.write(f"{_V}{padded}{_V}\n")

            # Bottom border
            out.write(f"{_BL}{_H * inner}{_BR}\n")

        out.flush()

    def clear(self) -> None:
        if sys.platform == "win32":
            os.system("cls")
        else:
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()

    def size(self) -> TerminalSize:
        try:
            cols, rows = os.get_terminal_size()
            return TerminalSize(columns=cols, rows=rows)
        except OSError:
            return TerminalSize(columns=80, rows=24)
