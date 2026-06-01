"""Convert a Jira XML/RSS export into one Markdown note per issue.

Usage: jira_xml_to_md.py <input.xml> <output_dir> [research_project_name]

Produces <ISSUE-KEY>.md files with frontmatter and wikilinks (parent, subtasks,
linked issues) so the tickets form a graph in Obsidian. Descriptions, custom
fields, and comments are converted from HTML to Markdown.
"""
import html as _html
import os
import re
import sys
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

try:
    from markdownify import markdownify as _md
except Exception:
    _md = None


def to_md(htmltext: str) -> str:
    if not htmltext:
        return ""
    if _md:
        try:
            return _md(htmltext, heading_style="ATX").strip()
        except Exception:
            pass
    t = re.sub(r"<br\s*/?>", "\n", htmltext)
    t = re.sub(r"</p>", "\n\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    return _html.unescape(t).strip()


def fmt_date(s: str) -> str:
    if not s:
        return ""
    try:
        return parsedate_to_datetime(s).strftime("%Y-%m-%d")
    except Exception:
        return s


def text(el) -> str:
    return (el.text or "").strip() if el is not None else ""


def yesc(s: str) -> str:
    return (s or "").replace('"', "'").replace("\n", " ").strip()


def main() -> int:
    argv = sys.argv[1:]
    skip_existing = "--skip-existing" in argv
    pos = [a for a in argv if not a.startswith("--")]
    if len(pos) < 2:
        print("usage: jira_xml_to_md.py <input.xml> <output_dir> [research_project] [--skip-existing]", file=sys.stderr)
        return 2
    src, outdir = pos[0], pos[1]
    research_project = pos[2] if len(pos) > 2 else "Project"
    os.makedirs(outdir, exist_ok=True)

    root = ET.parse(src).getroot()
    items = root.findall(".//item")
    written = 0
    skipped = 0
    for it in items:
        key = text(it.find("key"))
        if not key:
            continue
        out_path = os.path.join(outdir, f"{key}.md")
        if skip_existing and os.path.exists(out_path):
            skipped += 1
            continue
        summary = text(it.find("summary")) or text(it.find("title"))
        link = text(it.find("link"))
        itype = text(it.find("type"))
        status = text(it.find("status"))
        priority = text(it.find("priority"))
        assignee = text(it.find("assignee"))
        reporter = text(it.find("reporter"))
        proj_el = it.find("project")
        jira_project = text(proj_el)
        jira_key = proj_el.attrib.get("key", "") if proj_el is not None else ""
        parent = text(it.find("parent"))
        created = fmt_date(text(it.find("created")))
        updated = fmt_date(text(it.find("updated")))
        components = [text(c) for c in it.findall("component") if text(c)]
        fixversions = [text(c) for c in it.findall("fixVersion") if text(c)]
        labels = [text(l) for l in it.findall("./labels/label") if text(l)]

        desc_el = it.find("description")
        desc = to_md(desc_el.text if desc_el is not None else "")

        cfs = []
        for cf in it.findall("./customfields/customfield"):
            name = text(cf.find("customfieldname"))
            vals = []
            for v in cf.findall("./customfieldvalues/customfieldvalue"):
                raw = v.text or ""
                vals.append(to_md(raw) if "<" in raw else raw.strip())
            vals = [v for v in vals if v]
            if name and vals:
                cfs.append((name, vals))

        comments = []
        for cm in it.findall("./comments/comment"):
            comments.append((cm.attrib.get("author", ""), fmt_date(cm.attrib.get("created", "")), to_md(cm.text)))

        subtasks = [text(s) for s in it.findall("./subtasks/subtask") if text(s)]
        linked = list(dict.fromkeys(text(k) for k in it.findall(".//issuelinks//issuekey") if text(k)))

        fm = [
            "---",
            f'title: "{yesc(key + " " + summary)}"',
            "source_type: jira",
            f"origin: {link}",
            f"key: {key}",
            f'issue_type: "{yesc(itype)}"',
            f'status: "{yesc(status)}"',
            f'priority: "{yesc(priority)}"',
            f'assignee: "{yesc(assignee)}"',
            f'reporter: "{yesc(reporter)}"',
            f'jira_project: "{yesc(jira_project)} ({jira_key})"',
            f"created: {created}",
            f"updated: {updated}",
            f'project: "{yesc(research_project)}"',
            "tags: [research-source, jira]",
            "---",
            "",
        ]

        body = [f"# {key}: {summary}", "", f"[{key}]({link})", ""]
        meta = []
        for label, val in [("Type", itype), ("Status", status), ("Priority", priority),
                           ("Assignee", assignee), ("Reporter", reporter),
                           ("Components", ", ".join(components)), ("Fix Versions", ", ".join(fixversions)),
                           ("Labels", ", ".join(labels))]:
            if val:
                meta.append(f"- {label}: {val}")
        if meta:
            body += meta + [""]
        if desc:
            body += ["## Description", "", desc, ""]
        if cfs:
            body += ["## Fields", ""]
            for name, vals in cfs:
                body.append(f"### {name}")
                body += ([vals[0]] if len(vals) == 1 else [f"- {v}" for v in vals])
                body.append("")
        if comments:
            body += ["## Comments", ""]
            for author, cdate, cbody in comments:
                body += [f"**{author}** ({cdate}):", "", cbody, ""]
        link_lines = []
        if parent:
            link_lines.append(f"- Parent: [[{parent}]]")
        if subtasks:
            link_lines.append("- Subtasks: " + ", ".join(f"[[{s}]]" for s in subtasks))
        if linked:
            link_lines.append("- Linked: " + ", ".join(f"[[{l}]]" for l in linked))
        if link_lines:
            body += ["## Links", ""] + link_lines + [""]

        content = "\n".join(fm) + "\n".join(body).rstrip() + "\n"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        written += 1

    msg = f"Wrote {written} ticket notes to {outdir}"
    if skip_existing:
        msg += f" (skipped {skipped} already-existing)"
    print(msg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
