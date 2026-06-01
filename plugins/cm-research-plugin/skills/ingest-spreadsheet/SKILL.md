---
name: ingest-spreadsheet
description: This skill should be used when the user wants to bring a spreadsheet (.csv, .xls, .xlsx) into their Obsidian project-research workspace as a Markdown note with tables. Converts each sheet to a Markdown table with a summary, adds frontmatter, and files it under the project's Sources folder. Part of the cm-research-plugin ingestion stage.
version: 0.1.0
---

# Ingest Spreadsheet

Convert a CSV or Excel workbook into a Markdown source note with tables, in the project's Obsidian workspace.

## When to use this skill

When the user points at a `.csv`, `.xls`, or `.xlsx` and wants it in their research workspace. The output note feeds `generate-research`.

## Output location

Resolve the output root in this order, and state which was used:
1. An explicit path in the request.
2. The `CM_RESEARCH_OUTPUT_ROOT` environment variable, if set.
3. A fallback you confirm with the user before writing.

Write to `<project name>/Sources/`. Ask for the project name if unclear. Create folders as needed.

## One-time toolchain setup

If conversion fails on missing dependencies:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/setup-toolchain.sh"
```

## Convert

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/spreadsheet_to_md.py" "<input.csv|.xls|.xlsx>" "<output.md>"
```

The script writes one section per sheet, each with a row/column summary and a Markdown table. Large sheets are truncated to a preview row count (the script notes this); for analysis on the full dataset, keep the original file and reference it.

## Write the source note

Prepend frontmatter and review:

```yaml
---
title: <workbook or file name>
source_type: spreadsheet
origin: <original file path>
ingested: <YYYY-MM-DD>
project: <project name>
tags: [research-source, spreadsheet]
---
```

Add a short summary describing what the data represents (columns, what each row is, time range if relevant) so `generate-research` can reason about it without re-reading every row.

## Hand-off

Report where the note was written and offer to ingest more or proceed to `generate-research`.
