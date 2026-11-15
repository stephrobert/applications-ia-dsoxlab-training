# Governing and Securing AI-Generated Applications: verifiable labs

**Language:** [English](./README.md) · [Français](./README.fr.md)

[![CI](https://github.com/stephrobert/applications-ia-dsoxlab-training/actions/workflows/ci.yml/badge.svg)](https://github.com/stephrobert/applications-ia-dsoxlab-training/actions/workflows/ci.yml)
[![OpenSSF Scorecard](https://img.shields.io/ossf-scorecard/github.com/stephrobert/applications-ia-dsoxlab-training?label=OpenSSF%20Scorecard)](https://securityscorecards.dev/viewer/?uri=github.com/stephrobert/applications-ia-dsoxlab-training)
[![Plumber compliance](https://score.getplumber.io/github.com/stephrobert/applications-ia-dsoxlab-training.svg)](https://score.getplumber.io/github.com/stephrobert/applications-ia-dsoxlab-training)
[![SLSA 3](https://slsa.dev/images/gh-badge-level3.svg)](https://slsa.dev)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](./LICENSE)

A catalog of **verifiable labs** for the course « Governing and Securing
AI-Generated Applications » on Stéphane Robert's blog, played by the
[dsoxlab](https://github.com/stephrobert/dsoxlab) CLI. It is for the CISOs, IT
directors and managers who decide whether to host an application built with
AI, the engineers who run it, and the developers who vibe code and want to do
it with a method. Starting page until the lessons exist:
[vibe coding](https://www.stephane-robert.info/docs/developper/vibe-coding/) (in French).

## What it is

At the end of level 1, the learner can classify an application by its data,
its flows, its users and its criticality, and apply the policy of its class.
They can review an agent's changes against a specification and refuse the one
that disables a test, and check the dependencies an agent proposes before
installing them.

**No lab calls a real AI service or needs an API key.** The agent and its
proposals are provided files, deterministic: the same lab gives the same
result on every machine, with no account and no network.

## Requirements

The measured versions are pinned in [`mise.toml`](./mise.toml).

- **Python 3.11+ and [`uv`](https://docs.astral.sh/uv/)**
- **`git`**
- **`dsoxlab`**, the engine, installed as a standalone tool (see below).

Level 1 has **no `vm` lab**: `dsoxlab provision` is never called, and no network
access is needed (the package registry of `vc-paquet-inexistant` is a local
directory).

`dsoxlab doctor` says what this repository needs and what it does not, and
tells apart a check that failed from one it could not measure.

## Install

`dsoxlab` is published on [PyPI](https://pypi.org/project/dsoxlab/). Install it
as a standalone tool, so it stays out of this repository:

```bash
# 1. The dsoxlab CLI (external tool, stays out of this repo)
uv tool install dsoxlab

# 2. This lab catalog
git clone <this repository>
cd applications-ia-dsoxlab-training

# 3. Check the contract is valid
dsoxlab validate-structure
```

### Your first lab, in five minutes

```bash
export LAB_HOME=$PWD
dsoxlab list-labs                # the catalog, in teaching order
dsoxlab run       <id>           # set the starting state
dsoxlab challenge <id>           # read the mission
dsoxlab check     <id>           # run the tests, record the score
```

`run` is what prepares the lab. Running `check` on a lab you never started
measures nothing, and says so rather than recording a 0.

### Keeping it up to date

```bash
uv tool upgrade dsoxlab        # the engine, published on PyPI
git -C <this repo> pull        # the catalog
```

The engine and the catalog move independently: a new `dsoxlab` never requires
re-cloning the labs, and new labs never require upgrading the tool, as long as
the contract version matches.

## How it works

### The engine, documented where it lives

This catalog is played by `dsoxlab`, which documents its own contract and
commands. This README does not repeat them, so that it cannot drift when the
engine changes (dsoxlab issue #201):

- the contract: `meta.yml`, `lab.yaml`, `lab.<lang>.yaml`, the runtimes and
  their fields: [contract](https://github.com/stephrobert/dsoxlab/blob/main/docs/contract-v1.md);
- the commands and the life of a lab, from `run` to `check`:
  [commands](https://github.com/stephrobert/dsoxlab/blob/main/docs/commands.md) and [playing a lab](https://github.com/stephrobert/dsoxlab/blob/main/docs/learner.md);
- writing a lab, and what `validate-structure` checks:
  [catalog author guide](https://github.com/stephrobert/dsoxlab/blob/main/docs/catalog-author.md).

### Runtimes

Level 1 uses the `shell` runtime only.

| Runtime | What the lab asks for |
|---|---|
| `shell` | a terminal, Python 3.11 or later and `git`; nothing else |

### The validation model

Validation **proves the state, it does not trust the learner**. Each lab ships
`pytest` tests under `challenge/tests/` that read what the system holds, never
what a file contains or which commands were typed.

And a lab is proven **in both directions**: the tests must fail before the work
and pass after it. A test that is green before the work is not a test, it is an
assumption about the setup.

The reference solutions live in `labs/<id>/solution/` and are **encrypted**
(ansible-vault). `scripts/valider-labs.py` decrypts them when it lays them in the
working directory, and records each lab's verdict in `validation-labs.json`.

### Scoring, hints, progress

`check` records a score (tests passed out of total, minus the cost of any hints
revealed). Hints are **base64-encoded** in `challenge/hints.yaml`, so that
opening the file does not give them away, and their cost grows with their
precision. History lives in a SQLite database **local to this repository**.

A run that measured nothing is neither a pass nor a failure: if every collected
test skips, `check` records no score and says why. A score of 0 would accuse the
lab of what is missing from the machine.

## Catalog

### Level 1: classify, frame and vibe code with a method

| Lab | What it has you do | Time |
|---|---|---|
| [`vc-classifier-applications`](labs/vc-classifier-applications/) | Classify four AI-built applications and apply the policy of their class | 45 min |
| [`vc-contrat-applicatif`](labs/vc-contrat-applicatif/) | Write the contract of an AI-built application and keep the candidate repository from authorising itself | 45 min |
| [`vc-boucle-methode`](labs/vc-boucle-methode/) | Review an agent's changes against a specification and its tests | 40 min |
| [`vc-specification-agent`](labs/vc-specification-agent/) | Turn a business request into verifiable criteria and have an agent implement them | 50 min |
| [`vc-reprise-session`](labs/vc-reprise-session/) | Resume an interrupted coding session from Git, not from memory | 40 min |
| [`vc-paquet-inexistant`](labs/vc-paquet-inexistant/) | Check the dependencies an agent proposes before installing them | 30 min |
| [`vc-contexte-agent`](labs/vc-contexte-agent/) | Design the context of a coding agent and check what it really loaded | 45 min |
| [`vc-harness-agent-ia`](labs/vc-harness-agent-ia/) | Set up a minimal harness for a coding agent and test it on a simulated agent | 60 min |
| [`vc-epreuve-classification`](labs/vc-epreuve-classification/) | Level 1 test: qualify an undocumented application | 90 min |

### Claude Code: one mechanism per lab

| Lab | What it has you do | Time |
|---|---|---|
| [`cc-hook-qui-echoue`](labs/cc-hook-qui-echoue/) | Test a hook that succeeds, blocks and crashes | 45 min |
| [`cc-serveur-mcp-non-approuve`](labs/cc-serveur-mcp-non-approuve/) | Refuse an MCP server that a repository declares without approval | 30 min |
| [`cc-subagent-relecteur-borne`](labs/cc-subagent-relecteur-borne/) | Limit a reviewer subagent to the tools that read | 30 min |

## Contributing

Read [`CONTRIBUTING.md`](./CONTRIBUTING.md). In short: a lab is proven **in both
directions** before it is merged, `dsoxlab validate-structure` is green, and the
statement exists in English and in French.

Anything user-facing is bilingual. A document translated on one side only is
reported by the validator, not left to goodwill.

## License

See [`LICENSE`](./LICENSE).
