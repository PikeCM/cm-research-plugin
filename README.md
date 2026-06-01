# cm-research

CloudMasonry project-research marketplace for Claude Code.

## Plugin: cm-research-plugin

Build a local, Obsidian-based research workspace for a project. Ingest source material into Markdown notes, then generate structured research against a standard template. Local-first and on-device for the file ingestion; Jira (and later Granola, Slack) come through existing MCP connectors rather than custom API code.

### Skills
- **ingest-document** - convert a `.docx` or `.pdf` into a Markdown source note.
- **ingest-spreadsheet** - convert a `.csv`, `.xls`, or `.xlsx` into Markdown tables.
- **ingest-jira** - pull Jira tickets via the Atlassian MCP connector into Markdown notes.
- **ingest-slack** - pull Slack channels/threads via the Slack MCP connector into Markdown notes.
- **ingest-granola** - search Granola meeting notes via the Granola MCP connector and pull them into Markdown notes.
- **generate-research** - synthesize the ingested notes into a research document using a standard template.

### Why Markdown
Obsidian only displays a fixed set of file types by default (Markdown, images, audio, video, PDF). Converting docs and spreadsheets to Markdown makes them first-class in the vault: visible, searchable, and linkable with `[[wikilinks]]`.

## Install

```
/plugin marketplace add <git-url>
/plugin install cm-research-plugin@cm-research
```

## Output layout

Each project gets one workspace folder under the output root:

```
<output root>/<project name>/
  Sources/
    <ingested source notes>.md
  <project name> - Research.md
```

The output root resolves as: an explicit path in the request, then the `CM_RESEARCH_OUTPUT_ROOT` environment variable, then a fallback the skill confirms with you. Set a personal default in your Claude Code settings `env` block:

```json
{
  "env": {
    "CM_RESEARCH_OUTPUT_ROOT": "C:\\Users\\you\\OneDrive\\Documents\\Obsidian Vault\\Project Research"
  }
}
```

## Toolchain

Document and spreadsheet conversion need a small Python environment. Run once:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/setup-toolchain.sh"
```

## Data handling

Source material and generated research are client-confidential. They stay local and out of git (`.gitignore` blocks docs, spreadsheets, PDFs, and research files). When using the Jira, Granola, or Slack connectors, scope them to the minimum access needed.
