---
name: ingest-document
description: This skill should be used when the user wants to bring a Word document or PDF (.docx, .doc, .pdf) into their Obsidian project-research workspace as a Markdown note. Converts the document to Markdown, adds frontmatter and wikilinks, and files it under the project's Sources folder. Part of the cm-research-plugin ingestion stage.
version: 0.1.0
---

# Ingest Document

Convert a Word document or PDF into a Markdown source note in the project's Obsidian workspace.

## When to use this skill

When the user points at a `.docx`, `.doc`, or `.pdf` and wants it pulled into their research workspace. The output note becomes input to `generate-research`.

## Output location

Resolve the output root in this order, and state which was used:
1. An explicit path in the request.
2. The `CM_RESEARCH_OUTPUT_ROOT` environment variable, if set.
3. A fallback you confirm with the user before writing.

Within the output root, write to `<project name>/Sources/`. Ask for the project name if it is not clear from the request. Create folders as needed.

## One-time toolchain setup

If conversion fails because dependencies are missing, run:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/setup-toolchain.sh"
```

## Convert

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/document_to_md.py" "<input.docx|input.pdf>" "<output.md>"
```

Use the local research venv if it exists (`~/.cloudmasonry/cm-research/venv`); otherwise run the setup script first.

## Write the source note

The script produces the body. Prepend frontmatter and review the result:

```yaml
---
title: <document title>
source_type: document
origin: <original file path>
ingested: <YYYY-MM-DD>
project: <project name>
tags: [research-source, document]
---
```

Then:
- Add a short summary at the top (2 to 4 sentences) of what the document contains.
- Where the document references people, systems, or other ingested items, add `[[wikilinks]]`.
- PDFs converted by text extraction can be messy (columns, headers, footers). Skim and flag any section that looks garbled rather than treating it as clean.

## Hand-off

Tell the user where the note was written and offer to ingest more sources or run `generate-research` once enough sources are in.
