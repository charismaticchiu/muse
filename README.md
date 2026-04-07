# muse

CLI art creation tool for engineers. Generate, iterate, and critique AI images from the terminal.

![demo](demo.gif)

Muse wraps text-to-image and vision APIs into a session-based workflow — start with a prompt, tweak it with natural language, get AI critique, and browse your iteration history in a local web gallery. Bring your own API keys.

| `muse new "a cozy cabin in a snowy forest, watercolor"` | `muse tweak "add warm golden light from the windows"` |
|:---:|:---:|
| ![Step 1](https://github.com/user-attachments/assets/eb2bc52c-4a6b-495c-8032-8b2fb92c9cd9) | ![Step 2](https://github.com/user-attachments/assets/08791ee8-d96c-4118-9167-4ed4f81ecb6e) |

## Prerequisites

- **Python 3.11+**
- **uv** (recommended) or pip

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Installation

```bash
# Clone and enter the project
git clone https://github.com/charismaticchiu/muse.git
cd muse

# Option A: use uv (handles venv + dependencies automatically)
uv sync

# Option B: use pip
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

## Quick Start

```bash
# Set at least one provider key
export OPENAI_API_KEY="sk-..."   # DALL-E 3 + GPT-4o
# or
export GEMINI_API_KEY="AI..."    # Gemini 2.0 Flash

# If you used uv sync:
uv run muse new "a cozy cabin in a snowy forest, watercolor style"

# If you used pip install -e .:
muse new "a cozy cabin in a snowy forest, watercolor style"
```

## The Loop

```bash
# Start a session
muse new "sunset over a calm ocean, oil painting"

# Iterate with natural language
muse tweak "make the sky more dramatic with storm clouds"

# Get AI feedback
muse review

# Try the roast persona for laughs
muse review --persona roast

# See iteration history
muse history

# Roll back
muse back

# Browse everything in the gallery
muse gallery
```

## Commands

| Command | Description |
|---|---|
| `muse new "<prompt>"` | Start a new session, generate first image |
| `muse tweak "<prompt>"` | Iterate on the current image |
| `muse review` | AI critiques the current image |
| `muse history` | Show iteration chain |
| `muse back [N]` | Roll back N steps (default 1) |
| `muse resume [name]` | List or resume sessions |
| `muse gallery` | Open web gallery in browser |
| `muse providers` | Show detected providers and status |
| `muse config` | Show or set configuration |

### Flags

- `--provider <name>` — force a specific provider (`new`, `tweak`)
- `--size <WxH>` — image dimensions (`new`, `tweak`)
- `--persona <name>` — review persona (`review`)
- `--from <step>` — branch from a specific step (`tweak`)
- `--port <N>` — gallery port (`gallery`)

## Providers

Muse auto-detects available providers from environment variables:

| Provider | Models | Key |
|---|---|---|
| OpenAI | DALL-E 3 (generate), GPT-4o (vision) | `OPENAI_API_KEY` |
| Gemini | Gemini 2.0 Flash (generate + vision) | `GEMINI_API_KEY` |

```bash
# Check what's available
muse providers
```

## Review Personas

AI critique is powered by configurable personas — markdown templates that shape the feedback style.

| Persona | Style |
|---|---|
| `collaborative` (default) | Friendly partner, suggests `muse tweak` commands |
| `critic` | Formal art analysis — composition, color theory, technique |
| `technical` | Factual description — debug prompt vs. output gaps |
| `roast` | Sarcastic critique with programming analogies |

```bash
muse review --persona critic
```

Drop any `.md` file in `~/.muse/personas/` to create your own.

## Web Gallery

`muse gallery` starts a local server and opens a browser with:

- **Grid view** — all sessions as thumbnail cards
- **Timeline view** — step-by-step iteration chain with prompts and metadata

Dark theme. Auto-refreshes. No external dependencies.

## Session Storage

All data lives in `~/.muse/`:

```
~/.muse/
  sessions/
    cozy-cabin-snowy-forest/
      session.json
      steps/
        step-001.json
        step-001.png
        step-002.json
        step-002.png
  personas/
  config.toml
```

Steps are immutable — `muse back` moves a pointer, never deletes. History is always preserved.

## Configuration

```bash
# View current config
muse config

# Set defaults
muse config set provider openai
muse config set persona collaborative
muse config set size 1024x1024
muse config set preview terminal    # terminal | gallery | none
muse config set gallery_port 3333
```

## Development

```bash
# Install with dev dependencies
uv sync --extra dev

# Run tests
uv run pytest tests/ -v

# Run a specific test
uv run pytest tests/test_integration.py -v
```

Requires Python 3.11+.

## Tech Stack

- **CLI**: Click + Rich
- **AI**: OpenAI SDK, Google GenAI SDK
- **Gallery**: Python `http.server` + vanilla JS
- **Terminal images**: term-image
- **Config**: TOML

## Author

Ming-Chang Chiu — [@charismaticchiu](https://github.com/charismaticchiu)

## License

MIT
