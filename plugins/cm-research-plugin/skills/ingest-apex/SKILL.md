---
name: ingest-apex
description: This skill should be used when the user wants to bring a Salesforce Apex codebase (a folder of .cls classes and .trigger triggers) into their Obsidian project-research workspace as Markdown notes. Extracts structural metadata (declaration, methods, SOQL/SOSL, sObjects, DML, annotations, and class-to-class dependencies) into one note per class plus domain cluster notes and an architecture index, cross-linked with wikilinks. Structural only; no raw source is embedded. Part of the cm-research-plugin ingestion stage.
version: 0.1.0
---

# Ingest Apex

Turn a Salesforce Apex codebase into a navigable set of structural Markdown notes in the project's Obsidian workspace, so the code can be researched alongside documents, spreadsheets, and Jira.

## When to use this skill

When the user points at a folder of Apex classes (`.cls`) and triggers (`.trigger`) and wants the codebase pulled into their research workspace. The output notes become input to `generate-research`.

This skill produces **structural metadata only**, not raw code: each note records the class declaration, methods, SOQL/SOSL queries, sObjects referenced, DML operations, annotations, and which other classes it invokes and is invoked by. That keeps the vault navigable and research-friendly rather than burying findings under thousands of lines of source.

## Locate the source directories

A Salesforce DX project keeps Apex under `force-app/main/default/classes` and `force-app/main/default/triggers`. Confirm both with the user if the layout is non-standard.

- Point `--classes` at the classes directory and `--triggers` at the triggers directory.
- The script never descends into `.sfdx`, `.sf`, `node_modules`, or `.git`, so SFDX cache copies of the source are excluded automatically. If the path the user gives contains nested SDX projects, confirm which tree is the real source before running.

## No local toolchain needed

The parser is pure Python standard library, so it runs on any Python 3 already on the machine. No venv or `setup-toolchain.sh` is required for this skill.

## Output location

Resolve the output root in this order, and state which was used:
1. An explicit path in the request.
2. The `CM_RESEARCH_OUTPUT_ROOT` environment variable, if set.
3. A fallback you confirm with the user before writing.

Within the output root, everything is written under `<project>/Sources/Apex/`:
- `Classes/<Name>.md` - one note per Apex class
- `Triggers/<Name>.md` - one note per trigger
- `Clusters/<domain>.md` - a summary per name-prefix domain
- `_Apex Architecture Index.md` - the top-level structural index (roles, domains, integration/async surface, trigger-to-object map, most-referenced classes, most-touched sObjects)

## Convert

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/apex_to_md.py" \
  --classes "<.../force-app/main/default/classes>" \
  --triggers "<.../force-app/main/default/triggers>" \
  --out "<output root>/<project>/Sources" \
  --project "<research project name>"
```

Useful flags:
- `--dry-run` reports how many classes and triggers would be written and the role breakdown, writing nothing. Run this first on a large codebase so the user knows the scale before committing.
- `--include-tests` ingests `*Test` / `@isTest` classes too. The default excludes them, since they describe coverage rather than system behavior and roughly double the note count.
- `--limit N` parses only the first N classes, for a quick sample.

## Review the result

The notes are generated deterministically, but the extraction is regex-based and approximate, not a true Apex compiler. After a run:
- Spot-check a few notes against their source: declaration, methods, sObjects, and the invokes/invoked-by links.
- Open the architecture index first; it is the best entry point and the most useful single input to `generate-research`.
- Roles are inferred from interfaces, annotations, and naming suffixes (Service, Controller, Batch, Selector, and so on). Reclassify by hand only if a note is clearly mislabeled.

## Scale and data handling

- Confirm scope before ingesting very large codebases; lead with a `--dry-run`.
- Treat the source code as client-confidential; notes stay in the local vault and out of git.

## Hand-off

Report how many class, trigger, and cluster notes were written and where, point the user at the architecture index, and offer to ingest more sources or run `generate-research`.
