---
name: ingest-granola
description: This skill should be used when the user wants to search Granola meeting notes and pull relevant meetings into their Obsidian project-research workspace as Markdown notes. Uses the Granola MCP connector (read-only, no custom API) to search and retrieve notes, then writes each as a Markdown source note with frontmatter and wikilinks. Part of the cm-research-plugin ingestion stage.
version: 0.1.0
---

# Ingest Granola

Search Granola meeting notes and pull the relevant ones into the project's Obsidian workspace as Markdown source notes, using the Granola MCP connector.

## When to use this skill

When the user wants meeting notes from Granola captured into their research workspace: a search by topic, attendee, or date range, or a specific meeting.

## Authentication first

This skill uses the Granola MCP connector, not local scripts or custom API code. The connector must be authenticated before it can search or read. If only an authentication step is available (no search/read tools yet), ask the user to authenticate Granola first, then proceed. Use read-only access.

## How to search and fetch

1. Turn the user's intent into a search: a keyword/topic, a date range, or an attendee. Confirm the scope if the request is broad, to avoid pulling a large history.
2. Use the connector's search/list tools to find matching meetings, then retrieve each meeting's notes (and transcript, if available and wanted).
3. Show the user the candidate matches before bulk-ingesting, so they can confirm which meetings are relevant.

## Output location

Resolve the output root: explicit path in the request, then `CM_RESEARCH_OUTPUT_ROOT`, then a confirmed fallback. Write notes to `<project name>/Sources/`. One note per meeting, with a meaningful filename (for example `Granola - <meeting title> - <date>.md`).

## Write each note

```yaml
---
title: <meeting title>
source_type: granola
origin: <Granola meeting link or id>
meeting_date: <YYYY-MM-DD>
attendees: [<name>, <name>]
project: <project name>
tags: [research-source, granola, meeting]
---
```

Body:
- A 2 to 4 sentence summary: what the meeting was about and any decisions or action items.
- The structured notes (agenda, discussion, decisions, action items). Include the transcript only if the user wants it, since transcripts are long.
- Cross-link attendees and related items (projects, tickets, other meetings) with `[[wikilinks]]`.

## Scale and data handling

- Confirm scope before bulk pulls; do not ingest an entire meeting history silently.
- Meeting content is client-confidential: it stays in the local vault, out of git, with the connector scoped to minimum read access.

## Hand-off

Report which meetings were captured and offer to ingest more sources or run `generate-research`.
