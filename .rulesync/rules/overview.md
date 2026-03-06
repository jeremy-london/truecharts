---
root: true # true for overview files (e.g., AGENTS.md, overview.md), false for detail files (e.g., .agents/memories/*.md)
localRoot: false # (optional, default: false) true for project-specific local rules; false for global rules
targets: ["*"] # * = all tools, or specify tool names
description: "Rulesync project overview and development guidelines for unified AI rules management CLI tool"
globs: ["**/*"] # file patterns to match (e.g., ["*.md", "*.txt"])
cursor:
  alwaysApply: true
  description: "Rulesync project overview and development guidelines for unified AI rules management CLI tool"
  globs: ["*"]
antigravity:
  trigger: "always_on" # always_on, glob, manual, or model_decision
  globs: ["**/*"] # (optional) file patterns to match when trigger is "glob"
  description: "When to apply this rule" # (optional) used with "model_decision" trigger
---

# TrueCharts .rulesync Rules Overview

## Project Purpose

This repository is a TrueCharts-compatible Helm chart catalog, designed for managing and deploying containerized applications on TrueNAS SCALE servers. It leverages the .rulesync system to unify, automate, and standardize chart versioning, update workflows, and AI-driven configuration management.

## .rulesync System

- **.rulesync/skills/**: Contains skills (automation instructions) for tasks like finding the latest version of a chart, updating charts, and ensuring TrueNAS SCALE compatibility.
- **.rulesync/rules/**: Contains rules and best practices for chart management, including folder-based versioning, semantic versioning, and update detection for TrueNAS SCALE.
- **rulesync.jsonc**: The main configuration file for rulesync, defining how rules and skills are applied across the repo.

## Key Features

- **Folder-based Chart Versioning**: Each chart version lives in its own folder, as required by TrueNAS SCALE for update detection.
- **Automated Version Discovery**: Skills/scripts can find the latest container image versions and automate chart updates.
- **Declarative & AI-Driven**: Uses declarative rules and AI skills to keep the catalog up to date and consistent.
- **TrueNAS SCALE Focus**: All workflows and rules are tailored for seamless operation with TrueNAS SCALE's app system.

## Usage

- Add or update charts by creating a new versioned folder, copying the previous version, and updating Chart.yaml.
- Use rulesync CLI and skills to automate version checks, updates, and configuration file generation.
- Follow the rules in .rulesync/rules/ for all chart and catalog changes.

## Front Matter for Rule and Skill Files

All rules and skills must include a YAML front matter block at the top of the file. This block configures how the rule or skill is applied and interpreted by the rulesync system and compatible AI tools.

### Rule File Example (`rulesync/rules/*.md`)

```yaml
---
root: true # true for overview files, false for detail files
localRoot: false # (optional) true for project-specific local rules
targets: ["*"] # * = all tools, or specify tool names
description: "Rulesync project overview and development guidelines for unified AI rules management CLI tool"
globs: ["**/*"] # file patterns to match
agentsmd:
  subprojectPath: "path/to/subproject"
cursor:
  alwaysApply: true
  description: "Rulesync project overview and development guidelines for unified AI rules management CLI tool"
  globs: ["*"]
antigravity:
  trigger: "always_on"
  globs: ["**/*"]
  description: "When to apply this rule"
---
```

### Skill File Example (`.rulesync/skills/*/SKILL.md`):

```yaml
---
name: example-skill # skill name
description: >-
  A sample skill that demonstrates the skill format
targets: ["*"] # * = all, or specific tools
claudecode:
  model: sonnet # opus, sonnet, haiku, or any string
  allowed-tools:
    - "Bash"
    - "Read"
    - "Write"
    - "Grep"
  disable-model-invocation: true # (optional)
codexcli:
  short-description: A brief user-facing description
---
```

### Front Matter Guidelines

- Always use valid YAML syntax between `---` delimiters at the top of the file.
- Set `root: true` for overview or root-level rule files; use `root: false` for detail or subproject files.
- Use `targets` to specify which tools the rule or skill applies to (`["*"]` for all).
- Add a clear `description` for discoverability and maintainability.
- For skills, include tool-specific configuration blocks (e.g., `claudecode`, `codexcli`) as needed.
- For rules, use `globs` to define file patterns the rule applies to.
- See the examples above for recommended structure.

## Goal

To provide a robust, automated, and TrueNAS SCALE-compatible chart repository for managing containers and apps, with a focus on maintainability, automation, and best practices.
