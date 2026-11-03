# Krita Agent

[English](README.md) | [简体中文](README.zh-CN.md)

Krita Agent is a planned local drawing automation project for Windows. An independent Python controller and a custom plugin running inside Krita will work together to use Krita's native brushes and produce reproducible, editable, layered artwork.

> **Status: planning.** This repository contains documentation and directory placeholders only. There is no working CLI, plugin, installer, or automated drawing implementation yet. Commands, protocols, and features shown in the documentation are proposals; their feasibility must be verified against the target Krita builds.

## Goals

- Draw with Krita's native painting engine rather than simply importing externally generated images.
- Describe the canvas, layers, brush, trajectories, pressure, and outputs as structured tasks.
- Save an editable layered `.kra` document and export preview images.
- Probe the actual capabilities of stable and Next builds and select or fall back to a verified drawing path.
- Track upstream Krita changes and produce traceable compatibility reports and candidate tests.
- Optionally add natural-language planning and visual feedback later; the basic drawing pipeline should not depend on a cloud model.

```text
User / external program → Windows Python CLI / SDK → controlled local IPC → Krita Python Bridge → native painting engine
```

A normal external Python process cannot control another Krita process simply by importing `krita`. The proposed in-process plugin provides a controlled bridge. WSL2 is not an initial dependency.

## Technical direction

The planned stack is Windows Python 3, Krita Python / LibKis API, a Krita Python Extension, the Qt / PyQt bindings supplied by the target build, local IPC, and JSON with a schema. Git, virtual environments, and pytest are proposed for development and testing. The CLI framework, transport, and version constraints remain to be decided after prototyping. Test Qt5 builds first, then verify Qt6 compatibility.

Pressure-sensitive drawing will first investigate Next's continuous-stroke interface and a feasible segmented fallback for stable builds. An API appearing in source or documentation does not mean it exists in the installed build; brush response to pressure also requires separate validation.

## Documentation

- [Full design](docs/DESIGN.md): feature inventory, technical approach, draft protocol, workflows, pressure, upstream tracking, and references.
- [Roadmap and acceptance](docs/ROADMAP.md): milestones and real drawing acceptance criteria.
- [Architecture and safety boundaries](docs/ARCHITECTURE.md): component responsibilities, capability verification, and deployment principles.
- [Contributing](CONTRIBUTING.md): branching, review, validation, and bilingual README maintenance.

## Repository layout

```text
src/krita_agent/   Independent controller (placeholder)
plugin/            Krita Bridge (placeholder)
tests/             Tests (placeholder)
examples/          Examples (placeholder)
scripts/           Installation and maintenance scripts (placeholder)
docs/              Design and roadmap
```

Krita installations, upstream source clones, personal resources, caches, and bulk artwork do not belong in this repository. Installation and usage instructions will be added when a runnable version exists.

## License

Original project content is licensed under the [MIT License](LICENSE), copyright Yan Pengrui. Krita and third-party components have their own licenses; review applicable obligations before implementing and distributing the plugin.
