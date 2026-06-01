---
name: ingest-jira
description: This skill should be used when the user wants to pull Jira tickets/issues into their Obsidian project-research workspace as Markdown notes. Uses the Atlassian MCP connector (no custom API code) to fetch issues by JQL or key, then writes each as a Markdown note with frontmatter and wikilinks. Part of the cm-research-plugin ingestion stage.
version: 0.1.0
---

# Ingest Jira

Pull Jira issues into the project's Obsidian workspace as Markdown notes, using the Atlassian MCP connector.

## When to use this skill

When the user wants Jira tickets in their research workspace, by project, board, sprint, JQL query, or specific keys.

There are two ingestion paths:
- **Live connector** (default): pull from Jira directly via the Atlassian MCP connector (below).
- **XML/RSS export file**: if the user has a Jira XML export (the RSS-format export of a filter or search), convert it offline, no connector needed:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/jira_xml_to_md.py" "<export.xml>" "<output dir>" "<research project name>"
```

This writes one `<ISSUE-KEY>.md` per issue with frontmatter and wikilinks (parent, subtasks, linked issues). It uses the conversion toolchain; run `setup-toolchain.sh` first (it installs `markdownify` for the HTML descriptions and comments).

## No local toolchain needed

This skill uses the Atlassian MCP connector, not local scripts or custom API code. If the connector is not authenticated, ask the user to authenticate it first. Request only the access needed (read).

## How to fetch

1. If the cloud/site is unknown, list accessible resources and visible projects first (the connector provides tools for this).
2. Resolve the user's intent into a JQL query (for example `project = ABC AND sprint in openSprints()` or `project = ABC AND updated >= -30d`). Confirm the JQL with the user if their request is broad, to avoid pulling thousands of issues.
3. Search issues with the connector's JQL search tool, then fetch full detail per issue as needed (description, comments, status, assignee, links).

## Output location

Resolve the output root: explicit path in the request, then `CM_RESEARCH_OUTPUT_ROOT`, then a confirmed fallback. Write notes to `<project name>/Sources/`. One note per issue, filename `<ISSUE-KEY>.md`.

## Write each issue note

```yaml
---
title: <ISSUE-KEY> <summary>
source_type: jira
origin: <issue URL>
key: <ISSUE-KEY>
status: <status>
issue_type: <type>
assignee: <assignee>
priority: <priority>
updated: <YYYY-MM-DD>
project: <project name>
tags: [research-source, jira]
---
```

Body: the summary, description, acceptance criteria if present, and a condensed comment history. Cross-link related issues and epics as `[[ISSUE-KEY]]` so linked tickets form a graph in Obsidian. Note any issue blocked or linked to others.

## Scale and data handling

- Confirm scope before bulk pulls; do not silently retrieve very large result sets.
- Treat ticket content as client-confidential; it stays in the local vault and out of git.

## Hand-off

Report how many issues were written and offer to ingest more sources or run `generate-research`.
