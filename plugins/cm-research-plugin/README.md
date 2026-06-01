# cm-research-plugin

Ingest project sources into an Obsidian workspace and generate structured research.

## Stages
1. **Ingest** each source to a Markdown note in `<project>/Sources/`:
   - `ingest-document` for `.docx` / `.pdf`
   - `ingest-spreadsheet` for `.csv` / `.xls` / `.xlsx`
   - `ingest-jira` for Jira tickets (via the Atlassian MCP connector)
2. **Generate research** with `generate-research`, which synthesizes the source notes into `<project>/<project> - Research.md` using a standard template.

Notes carry frontmatter (source type, origin, ingest date) and cross-link with `[[wikilinks]]` so the workspace is navigable in Obsidian.

## Output location

Resolved as: explicit path in the request, then `CM_RESEARCH_OUTPUT_ROOT`, then a confirmed fallback. One workspace folder per project; do not commit client material (see `.gitignore`).

## Toolchain setup

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/setup-toolchain.sh"
```

Installs a local Python environment (pandas, openpyxl, xlrd, python-docx, pypdf, tabulate) for document and spreadsheet conversion. Jira ingestion needs no local toolchain; it uses the Atlassian MCP connector.

## Future sources
Granola and Slack are planned, also via their existing MCP connectors rather than custom API code.
