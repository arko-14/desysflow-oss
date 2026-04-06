# DesysFlow OSS

DesysFlow OSS is a local-first system design generator that turns source code and goals into versioned architecture artifacts.

It includes:
- A terminal-first CLI (`desysflow`) for generation and iteration
- A local FastAPI backend
- A lightweight React UI for prompting and artifact inspection

## Why DesysFlow

- Local-first workflow with repo-native outputs
- Versioned design artifacts (`v1`, `v2`, ...)
- Structured outputs (HLD, LLD, technical report, diagrams, diffs)
- Provider-flexible LLM support (`ollama`, `openai`, `anthropic`)

## Quick Start

### Prerequisites
- Python 3.11+
- `uv`
- Node.js + npm

### Cold Start

```bash
./letsvibedesign
```

Then choose a mode:

```bash
./letsvibedesign cli
./letsvibedesign dev
./letsvibedesign api
./letsvibedesign ui
```

## Core CLI Commands

```bash
desysflow chat --source . --out ./desysflow --project my-project
desysflow design --source . --out ./desysflow --project my-project
desysflow redesign --source . --out ./desysflow --project my-project --focus "improve scaling"
```

## Output Structure

DesysFlow writes versioned artifacts to `./desysflow/<project>/vN/` including:
- `HLD.md`
- `LLD.md`
- `TECHNICAL_REPORT.md`
- `NON_TECHNICAL_DOC.md`
- `PIPELINE.md`
- `diagram.mmd`
- `SOURCE_INVENTORY.md`
- `SUMMARY.md`
- `CHANGELOG.md`
- `DIFF.md`
- `METADATA.json`

## Documentation

- [Getting Started](docs/getting-started.md)
- [CLI Guide](docs/cli.md)
- [Architecture](docs/architecture.md)
- [Examples](docs/examples.md)
- [Project Overview](docs/project-overview.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Author

- X: [@kmeanskaran](https://x.com/kmeanskaran)
- Website: [kmeanskaran.com](https://kmeanskaran.com)

## Code of Conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
