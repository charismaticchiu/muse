"""Terminal inline image display with protocol auto-detection."""

import os
import sys
from pathlib import Path


def detect_protocol() -> str:
    """Detect the best image display protocol for the current terminal."""
    term_program = os.environ.get("TERM_PROGRAM", "")
    term = os.environ.get("TERM", "")

    if term_program == "iTerm.app":
        return "iterm"
    if term == "xterm-kitty":
        return "kitty"
    if term_program == "WezTerm":
        return "iterm"
    return "fallback"


def show_image(image_path: Path, preview_mode: str = "terminal") -> None:
    """Display an image in the terminal or suggest alternatives."""
    if preview_mode == "none":
        return

    if preview_mode == "gallery":
        print(f"  Image saved: {image_path}")
        print("  Run `muse gallery` to view in browser")
        return

    protocol = detect_protocol()

    if protocol == "fallback":
        try:
            from term_image.image import from_file
            img = from_file(str(image_path))
            img.draw()
            return
        except Exception:
            print(f"  Image saved: {image_path}")
            print("  Run `muse gallery` to view in browser")
            return

    if protocol == "iterm":
        _show_iterm(image_path)
    elif protocol == "kitty":
        _show_kitty(image_path)


def _show_iterm(image_path: Path) -> None:
    import base64
    image_data = base64.b64encode(image_path.read_bytes()).decode("ascii")
    sys.stdout.write(f"\033]1337;File=inline=1;width=auto;height=auto:{image_data}\a")
    sys.stdout.write("\n")
    sys.stdout.flush()


def _show_kitty(image_path: Path) -> None:
    import base64
    image_data = base64.b64encode(image_path.read_bytes()).decode("ascii")
    while image_data:
        chunk = image_data[:4096]
        image_data = image_data[4096:]
        m = 1 if image_data else 0
        sys.stdout.write(f"\033_Ga=T,f=100,m={m};{chunk}\033\\")
    sys.stdout.write("\n")
    sys.stdout.flush()
