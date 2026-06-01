---
name: ingest-slack
description: This skill should be used when the user wants to pull Slack messages, threads, or channel history into their Obsidian project-research workspace as Markdown notes. Uses the Slack MCP connector (read-only, no custom API) to fetch conversations, then writes them as Markdown source notes with frontmatter and wikilinks. Part of the cm-research-plugin ingestion stage.
version: 0.1.0
---

# Ingest Slack

Pull Slack conversations into the project's Obsidian workspace as Markdown source notes, using the Slack MCP connector.

## When to use this skill

When the user wants Slack content captured into their research workspace: a channel's history, a specific thread, or search results on a topic.

## No local toolchain needed

This skill uses the Slack MCP connector, not local scripts or custom API code. If the connector is not authenticated, ask the user to authenticate it first. Use read-only operations and request only the access needed.

## How to fetch

1. Identify the target with the user:
   - A channel (find it with the channel search tool, then read its messages).
   - A specific thread (read the thread by its reference).
   - A topic (run a public, or public-and-private, search).
2. Resolve user IDs to display names (the user-profile tool) so notes read naturally instead of showing raw `Uxxxx` IDs.
3. Confirm scope before any large pull (date range or message count). Do not export entire channels or workspaces silently.

## Output location

Resolve the output root: explicit path in the request, then `CM_RESEARCH_OUTPUT_ROOT`, then a confirmed fallback. Write notes to `<project name>/Sources/`. One note per channel, thread, or search, with a meaningful filename (for example `Slack - #channel - <topic or date range>.md`).

## Write each note

```yaml
---
title: Slack - #<channel> <topic or range>
source_type: slack
origin: <channel name and/or message permalink>
channel: "#<channel>"
date_range: <start to end>
project: <project name>
tags: [research-source, slack]
---
```

Body:
- A 2 to 4 sentence summary at the top: what the conversation is about and any decisions reached.
- A clean chronological transcript: `**<Display Name>** (<timestamp>): <message>`. Preserve thread structure by grouping replies under their parent.
- Cross-link people and related items with `[[wikilinks]]`. Include reactions only when they carry meaning (for example a decision being acknowledged).

## Scale and data handling

- Confirm scope before bulk pulls.
- Slack content is client-confidential: it stays in the local vault, out of git, with the connector scoped to minimum read access.
- Do not ingest direct messages or private channels unless the user explicitly asks.

## Hand-off

Report what was captured (channel, range, message count) and offer to ingest more sources or run `generate-research`.
