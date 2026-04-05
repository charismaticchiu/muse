"""Muse CLI — art creation tool for engineers."""

import json
import sys
from pathlib import Path

import click

from muse.config import (
    MuseConfig,
    detect_providers,
    ensure_muse_home,
    get_muse_home,
    load_config,
)
from muse.models import GeneratedImage
from muse.preview import show_image
from muse.providers import build_registry
from muse.review import ReviewEngine
from muse.session import SessionManager


def _get_context():
    """Load config, session manager, and provider registry."""
    muse_home = get_muse_home()
    ensure_muse_home(muse_home)
    config = load_config(muse_home)
    session_mgr = SessionManager(muse_home)
    registry = build_registry()
    return muse_home, config, session_mgr, registry


def _get_active_session(muse_home: Path) -> str | None:
    state_file = muse_home / ".active_session"
    if state_file.exists():
        return state_file.read_text().strip()
    return None


def _set_active_session(muse_home: Path, name: str) -> None:
    state_file = muse_home / ".active_session"
    state_file.write_text(name)


@click.group()
def main():
    """Muse — CLI art creation tool for engineers."""
    pass


@main.command()
@click.argument("prompt")
@click.option("--provider", default=None, help="Force a specific provider")
@click.option("--size", default=None, help="Image size (e.g. 1024x1024)")
def new(prompt, provider, size):
    """Start a new session and generate the first image."""
    muse_home, config, session_mgr, registry = _get_context()

    if provider:
        prov = registry.get(provider)
    elif config.provider != "auto":
        prov = registry.get(config.provider)
    else:
        prov = registry.get_auto()

    if prov is None:
        click.echo("\n  No API keys detected.\n")
        click.echo("  Set up a provider:")
        click.echo('    export OPENAI_API_KEY="sk-..."')
        click.echo('    export GEMINI_API_KEY="AI..."')
        click.echo("\n  Run: muse providers")
        sys.exit(1)

    session = session_mgr.create(prompt, provider=prov.name)
    click.echo(f"  Session: {session.name}")
    click.echo(f"  Provider: {prov.name}")

    step_num = 1
    output_path = (
        muse_home / "sessions" / session.name / "steps" / f"step-{step_num:03d}.png"
    )
    kwargs = {"output_path": output_path}
    if size or config.size:
        kwargs["size"] = size or config.size

    try:
        result = prov.generate(prompt, **kwargs)
    except Exception as e:
        click.echo(f"  Error: {e}", err=True)
        sys.exit(1)

    session_mgr.add_step(session.name, result, parent_step=None)
    _set_active_session(muse_home, session.name)

    click.echo("  Step 1 saved")
    show_image(result.path, config.preview)
    click.echo()
    click.echo("  Run `muse review` for AI feedback")
    click.echo('  Run `muse tweak "..."` to iterate')
    click.echo("  Run `muse gallery` for full browser view")


@main.command()
@click.argument("prompt")
@click.option("--provider", default=None, help="Force a specific provider")
@click.option("--size", default=None, help="Image size")
@click.option("--from", "from_step", default=None, type=int, help="Branch from step N")
def tweak(prompt, provider, size, from_step):
    """Iterate on the current image with a new prompt."""
    muse_home, config, session_mgr, registry = _get_context()

    session_name = _get_active_session(muse_home)
    if not session_name:
        click.echo("  No active session. Run `muse new` or `muse resume` first.")
        sys.exit(1)

    session = session_mgr.load(session_name)
    parent = from_step or session.current_step

    current_image = (
        muse_home / "sessions" / session_name / "steps" / f"step-{parent:03d}.png"
    )

    if provider:
        prov = registry.get(provider)
    elif config.provider != "auto":
        prov = registry.get(config.provider)
    else:
        prov = registry.get_auto()

    if prov is None:
        click.echo("  No providers available. Run `muse providers`.")
        sys.exit(1)

    step_num = session.total_steps + 1
    output_path = (
        muse_home / "sessions" / session_name / "steps" / f"step-{step_num:03d}.png"
    )
    kwargs = {"output_path": output_path}
    if size or config.size:
        kwargs["size"] = size or config.size

    try:
        result = prov.edit(current_image, prompt, **kwargs)
    except Exception as e:
        click.echo(f"  Error: {e}", err=True)
        sys.exit(1)

    session_mgr.add_step(session_name, result, parent_step=parent)
    click.echo(f"  Step {step_num} generated from step {parent}")
    show_image(result.path, config.preview)


@main.command()
@click.option("--persona", default=None, help="Review persona to use")
def review(persona):
    """Get AI critique of the current image."""
    muse_home, config, session_mgr, registry = _get_context()

    session_name = _get_active_session(muse_home)
    if not session_name:
        click.echo("  No active session. Run `muse new` or `muse resume` first.")
        sys.exit(1)

    persona_name = persona or config.persona
    _ensure_personas(muse_home)

    engine = ReviewEngine(muse_home)
    history = session_mgr.get_history(session_name)
    session = session_mgr.load(session_name)

    current_image = (
        muse_home / "sessions" / session_name / "steps"
        / f"step-{session.current_step:03d}.png"
    )

    if not current_image.exists():
        click.echo("  No image at current step.")
        sys.exit(1)

    vision_prov = registry.get_vision_provider()
    if vision_prov is None:
        click.echo("  No vision-capable provider available. Run `muse providers`.")
        sys.exit(1)

    try:
        result = engine.review(vision_prov, current_image, persona_name, history)
    except FileNotFoundError as e:
        click.echo(f"  {e}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"  Error: {e}", err=True)
        sys.exit(1)

    click.echo()
    click.echo(result)
    session_mgr.save_review(session_name, session.current_step, result)


@main.command()
def history():
    """Show iteration history for the current session."""
    muse_home, config, session_mgr, registry = _get_context()

    session_name = _get_active_session(muse_home)
    if not session_name:
        click.echo("  No active session. Run `muse new` or `muse resume` first.")
        sys.exit(1)

    session = session_mgr.load(session_name)
    steps = session_mgr.get_history(session_name)

    click.echo(f"  {session.name}")
    for step in steps:
        marker = " <- current" if step.step == session.current_step else ""
        parent_info = ""
        if step.parent_step is not None:
            parent_info = f" (from {step.parent_step})"
        click.echo(f'  {step.step}. "{step.prompt}"{parent_info}{marker}')


@main.command()
@click.argument("n", default=1, type=int)
def back(n):
    """Roll back N steps (default 1)."""
    muse_home, config, session_mgr, registry = _get_context()

    session_name = _get_active_session(muse_home)
    if not session_name:
        click.echo("  No active session.")
        sys.exit(1)

    session = session_mgr.back(session_name, n)
    click.echo(f"  Rolled back to step {session.current_step}")

    current_image = (
        muse_home / "sessions" / session_name / "steps"
        / f"step-{session.current_step:03d}.png"
    )
    if current_image.exists():
        show_image(current_image, config.preview)


@main.command()
@click.argument("name", required=False)
def resume(name):
    """List sessions or resume a specific one."""
    muse_home, config, session_mgr, registry = _get_context()

    if name:
        try:
            session = session_mgr.load(name)
        except (FileNotFoundError, json.JSONDecodeError):
            click.echo(f"  Session not found: {name}")
            sys.exit(1)

        _set_active_session(muse_home, name)
        click.echo(f"  Resumed: {session.name} (step {session.current_step}/{session.total_steps})")
        return

    sessions = session_mgr.list_sessions()
    if not sessions:
        click.echo("  No sessions found. Run `muse new` to start one.")
        return

    click.echo("  Sessions:")
    active = _get_active_session(muse_home)
    for s in sessions:
        marker = " *" if s.name == active else ""
        click.echo(f"    {s.name} ({s.total_steps} steps){marker}")


@main.command()
def providers():
    """List detected providers and their status."""
    muse_home, config, session_mgr, registry = _get_context()
    available = detect_providers()

    click.echo()
    click.echo("  Provider    Status")
    click.echo("  " + "-" * 30)

    provider_names = ["openai", "gemini"]
    for name in provider_names:
        status = "ready" if name in available else "no key"
        symbol = "+" if name in available else "-"
        click.echo(f"  {symbol} {name:<12} {status}")

    click.echo()
    if available:
        click.echo(f"  Active: {available[0]} (auto-detected)")
    else:
        click.echo("  No providers found. Set an API key:")
        click.echo('    export OPENAI_API_KEY="sk-..."')
        click.echo('    export GEMINI_API_KEY="AI..."')


@main.command()
@click.argument("args", nargs=-1)
def config(args):
    """Show or set configuration."""
    muse_home, cfg, session_mgr, registry = _get_context()

    if not args:
        click.echo(f"  provider: {cfg.provider}")
        click.echo(f"  persona:  {cfg.persona}")
        click.echo(f"  size:     {cfg.size}")
        click.echo(f"  preview:  {cfg.preview}")
        click.echo(f"  gallery:  port {cfg.gallery_port}")
        click.echo(f"\n  Config file: {muse_home / 'config.toml'}")
        return

    if len(args) >= 3 and args[0] == "set":
        key, value = args[1], args[2]
        _set_config_value(muse_home, key, value)
        click.echo(f"  Set {key} = {value}")
    else:
        click.echo("  Usage: muse config set <key> <value>")


@main.command()
@click.option("--port", default=None, type=int, help="Gallery port")
def gallery(port):
    """Launch the web gallery in your browser."""
    muse_home, config, session_mgr, registry = _get_context()
    gallery_port = port or config.gallery_port

    from muse.gallery.server import start_gallery
    start_gallery(muse_home, port=gallery_port)


def _set_config_value(muse_home: Path, key: str, value: str) -> None:
    import tomli_w
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib

    config_path = muse_home / "config.toml"
    if config_path.exists():
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    else:
        data = {}

    defaults = data.setdefault("defaults", {})
    try:
        value = int(value)
    except ValueError:
        pass
    defaults[key] = value

    with open(config_path, "wb") as f:
        tomli_w.dump(data, f)


def _ensure_personas(muse_home: Path) -> None:
    personas_dir = muse_home / "personas"
    bundled_dir = Path(__file__).parent.parent.parent / "data" / "personas"

    if not bundled_dir.exists():
        return

    for persona_file in bundled_dir.glob("*.md"):
        dest = personas_dir / persona_file.name
        if not dest.exists():
            dest.write_text(persona_file.read_text())
