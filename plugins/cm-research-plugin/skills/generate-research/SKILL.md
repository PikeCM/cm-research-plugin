---
name: generate-research
description: This skill should be used when the user wants to generate or synthesize project research from the Markdown source notes already ingested into an Obsidian project workspace. Reads the project's Sources notes and produces a structured research document against a standard template, citing sources with wikilinks. Part of the cm-research-plugin.
version: 0.1.0
---

# Generate Research

Synthesize the ingested source notes for a project into a structured research document.

## When to use this skill

After sources have been ingested (via ingest-document, ingest-spreadsheet, ingest-jira) and the user wants research generated or refreshed. Requires a project workspace with a `Sources/` folder.

## Inputs

1. Resolve the project workspace: explicit path in the request, then `CM_RESEARCH_OUTPUT_ROOT` plus project name, then confirm with the user.
2. Read the primary source notes in `<project>/Sources/`. Use their frontmatter (source_type, origin) to understand what each is.
3. Also read any prior research notes in `<project>/Research/`. Treat these as a **derived, second-order datapoint**: useful prior conclusions and context, but not primary evidence. Prefer to re-ground their claims in the primary sources, and carry forward any of their unresolved Open Questions and Assumptions.

## Core rules

1. **Ground every claim in a source.** Each finding cites the source note(s) it comes from with `[[wikilinks]]`. Do not introduce facts that are not in the sources.
2. **Separate fact from inference.** State what the sources say, then label any synthesis or hypothesis as such.
3. **Surface gaps and conflicts.** Where sources disagree or are silent on something important, record it under Open Questions rather than smoothing it over.
4. **State assumptions explicitly.** Any conclusion depending on information not in the sources gets an assumption noted.
5. **Match the audience.** Plain English; define Salesforce acronyms on first use; business framing for findings, technical depth where the sources warrant it.
6. **Distinguish primary from derived.** When a finding rests only on a prior research note rather than a primary source, label it as derived, and verify it against the primary sources where possible before relying on it. Do not let a prior inference harden into fact; that is how errors compound across successive research.

## How to produce it

1. Read every primary source note in `<project>/Sources/`, plus any prior research notes in `<project>/Research/`.
2. Use the template at `${CLAUDE_PLUGIN_ROOT}/skills/generate-research/templates/research-template.md`.
3. Build the source inventory first (what you have, what each covers, including prior research consulted), then work through findings, themes, risks, and open questions, citing sources throughout.
4. Write to `<project>/Research/<topic> - Research.md`. Cross-link to the source notes and to any prior research you built on.

## Output

Summarize for the user: how many sources were synthesized, the main findings, and the most important open questions. Offer to refresh the research after more sources are ingested.
