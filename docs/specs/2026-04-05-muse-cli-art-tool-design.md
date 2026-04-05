# Muse — CLI Art Creation Tool for Engineers

**Date:** 2026-04-05
**Status:** Approved

## Overview

Muse is a CLI-first art creation tool that lets engineers generate, iterate, and critique AI-generated images through a multi-modal closed loop. It combines text-to-image generation, image-to-text critique, and natural language iteration — all from the terminal, with a browser-based gallery for rich visual browsing.

**Core philosophy:** Start with the engineer's most accessible tool (CLI), make results easy to see (terminal inline + web gallery), and make iteration easy (natural language tweaks, session history, AI critique).

## Target Users

Engineers and technically-oriented people who want to explore art creation using tools they already know — the terminal and API keys they already have.

## Architecture: Layered Monolith

Single Python package with clean internal layers. Provider abstraction via a Python ABC, no plugin system. Web gallery served by the same process.

```
┌─────────────────────────────────────────────────┐
│                   muse CLI                       │
│            (entry point, commands)                │
├─────────────────────────────────────────────────┤
│              Session Manager                     │
│  creates/resumes sessions, tracks history chain  │
├──────────────┬──────────────┬───────────────────┤
│  Provider    │   Review     │   Web Gallery     │
│  Layer (ABC) │   Engine     │   Server          │
│              │              │                   │
│ ┌──────────┐ │ ┌──────────┐ │  Static HTML/JS   │
│ │ OpenAI   │ │ │ Personas │ │  served by Python │
│ │ Provider │ │ │ (markdown │ │  http.server.     │
│ ├──────────┤ │ │  files)  │ │  Auto-refreshes.  │
│ │ Gemini   │ │ └──────────┘ │                   │
│ │ Provider │ │              │                   │
│ └──────────┘ │              │                   │
├──────────────┴──────────────┴───────────────────┤
│              Config / Key Detection              │
│     ~/.muse/config.toml + env var scanning       │
└─────────────────────────────────────────────────┘
```

## CLI Commands

### Core Loop

| Command | Description |
|---|---|
| `muse new "<prompt>"` | Start new session, generate first image |
| `muse tweak "<prompt>"` | Natural language edit of current image |
| `muse review` | AI critiques current image using active persona |
| `muse history` | Show iteration chain for current session |
| `muse back [N]` | Roll back N steps (default 1). Moves pointer, never deletes |
| `muse resume [name]` | List sessions or resume a specific one |

### Utilities

| Command | Description |
|---|---|
| `muse gallery` | Launch web gallery in browser |
| `muse providers` | List detected providers and key status |
| `muse config` | Show/set configuration |

### Command Flags

- `--provider <name>` — force a specific provider (on `new` and `tweak`)
- `--size <WxH>` — override image dimensions
- `--persona <name>` — select review persona (on `review`)
- `--from <step>` — branch from a specific step (on `tweak`)
- `--port <N>` — custom gallery port (on `gallery`)

## Provider Abstraction

### Interface

```python
class ImageProvider(ABC):
    name: str

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> GeneratedImage: ...

    @abstractmethod
    def edit(self, image: Path, prompt: str, **kwargs) -> GeneratedImage: ...

    @abstractmethod
    def describe(self, image: Path, system_prompt: str) -> str: ...

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool: ...
```

Three methods:
- `generate` — text-to-image (`muse new`)
- `edit` — image + text-to-image (`muse tweak`)
- `describe` — image-to-text (`muse review`)

### GeneratedImage

```python
@dataclass
class GeneratedImage:
    path: Path           # saved image location
    prompt: str          # prompt used
    provider: str        # provider name
    metadata: dict       # provider-specific (model, seed, etc.)
```

### Bundled Providers

**OpenAI:** DALL-E 3 for generate/edit, GPT-4o for describe. Key: `OPENAI_API_KEY`.

**Gemini:** Gemini 2.0 Flash for generate, Gemini 2.0 Flash for describe. Key: `GEMINI_API_KEY`.

### Key Detection

1. Env vars: `OPENAI_API_KEY`, `GEMINI_API_KEY`
2. Config file (not recommended but supported)
3. `"auto"` mode: use first available provider

No keys found produces a helpful setup message with examples.

### Cross-Provider Review

Review requires a vision-capable model. If the active generation provider lacks vision capabilities, the review engine falls back to another available provider that supports vision, or errors with a helpful message.

## Session Management

### Storage Structure

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
        step-002-review.md
  personas/
    collaborative.md
    critic.md
    technical.md
  config.toml
```

### session.json

```json
{
  "name": "cozy-cabin-snowy-forest",
  "created": "2026-04-05T10:30:00Z",
  "current_step": 2,
  "provider": "openai",
  "total_steps": 2
}
```

### step-NNN.json

```json
{
  "step": 1,
  "prompt": "a cozy cabin in a snowy forest, watercolor style",
  "parent_step": null,
  "provider": "openai",
  "model": "dall-e-3",
  "timestamp": "2026-04-05T10:30:01Z",
  "image": "step-001.png",
  "metadata": {"size": "1024x1024", "revised_prompt": "..."}
}
```

### Key Behaviors

- **Session naming:** Slugified from the initial prompt. Collisions resolved with `-2`, `-3` suffix.
- **Steps are immutable:** `muse back` moves `current_step` pointer, never deletes steps. History is always preserved.
- **`muse tweak --from N`:** Creates a new step with `parent_step: N`, enabling branching from any point.

## Web Gallery

### Two Views

**Grid view (landing page):**
- All sessions as thumbnail cards (latest image, name, step count, last modified)
- Click a session to drill into timeline

**Timeline view (session detail):**
- Horizontal step chain showing iteration progression
- Selected step shown large with prompt, provider info, metadata
- Current step highlighted
- Review output shown alongside if available

### Technical Implementation

- Single-page app: one `index.html` with vanilla JS, no framework
- Python serves session data via `/api/sessions` and `/api/sessions/<name>` endpoints
- Auto-refreshes via polling every 2 seconds
- Dark theme (makes images pop)
- `muse gallery` starts server and opens browser via `webbrowser.open()`

## Terminal Inline Image Display

### Detection Priority

1. `TERM_PROGRAM=iTerm.app` — iTerm2 inline images
2. `TERM=xterm-kitty` — Kitty graphics protocol
3. `TERM_PROGRAM=WezTerm` — iTerm2 protocol (compatible)
4. Sixel support — Sixel encoding
5. Fallback — print file path, suggest `muse gallery`

### Implementation

Use the `term-image` Python library for broad protocol support. Configurable via `config.toml: preview = "terminal" | "gallery" | "none"`.

## Review Engine & Personas

### Flow

1. Load current step's image
2. Load persona template (markdown file from `~/.muse/personas/`)
3. Send to provider's `describe()`: system_prompt = persona template with session history (prior prompts and tweaks) appended as context, image = current step's image
4. Stream response to terminal
5. Save output to `step-NNN-review.md`

### Bundled Personas

| Persona | Tone | Purpose |
|---|---|---|
| `collaborative` (default) | Conversational, suggests next moves | General iteration partner |
| `critic` | Formal analysis | Composition, color, technique critique |
| `technical` | Factual description | Debug prompt-vs-output gaps |

### Custom Personas

Drop any `.md` file in `~/.muse/personas/` — immediately available via `muse review --persona <filename>`.

## Configuration

### config.toml

```toml
[defaults]
provider = "auto"
persona = "collaborative"
size = "1024x1024"
gallery_port = 3333
preview = "terminal"

[providers.openai]
model_generate = "dall-e-3"
model_vision = "gpt-4o"

[providers.gemini]
model_generate = "gemini-2.0-flash-exp"
model_vision = "gemini-2.0-flash"
```

### First-Run Experience

No keys detected produces a friendly setup guide with copy-paste-ready export commands and a link to `muse providers --help`.

## Tech Stack

- **Language:** Python 3.11+
- **CLI framework:** `click` (or `typer`)
- **AI SDKs:** `openai`, `google-genai`
- **Terminal images:** `term-image`
- **Web gallery:** Python `http.server` + vanilla HTML/JS
- **Config:** `tomli` / `tomli-w` for TOML parsing
- **Package management:** `uv` for development, distributable via `pip`

## Testing Strategy

- Unit tests for session management (create, back, resume, naming collisions)
- Unit tests for provider interface (mock API responses)
- Integration test for the full loop: new -> tweak -> review -> back
- Manual testing for terminal image display (protocol-dependent)
- Gallery tested via API endpoint responses (JSON correctness)

## Out of Scope (for v1)

- Branching/merging sessions (git-style)
- Project/album grouping
- Real-time collaborative sessions
- Image upload (generate from existing image without a session)
- Provider plugin discovery system
- Mobile/responsive gallery
