"""Convert a Salesforce Apex codebase into structural Markdown notes for research.

Usage:
  apex_to_md.py --classes <dir> [--triggers <dir>] --out <dir> --project <name>
                [--include-tests] [--limit N] [--dry-run]

Produces, under <out>/Apex/:
  Classes/<Name>.md     one note per Apex class (structural metadata only)
  Triggers/<Name>.md    one note per trigger
  Clusters/<domain>.md  a summary per name-prefix domain
  _Apex Architecture Index.md  the top-level structural index

Each note carries frontmatter and Obsidian [[wikilinks]] for the classes it
invokes and is invoked by, so the codebase forms a navigable graph. Extraction
is structural (declaration, methods, SOQL/SOSL, sObjects, DML, annotations,
dependencies) - no raw source is embedded. Test classes are skipped unless
--include-tests is given. Pure standard library; no venv required.

Regex-based parsing is approximate, not a true Apex grammar; it is calibrated
for research-grade structure, not compilation.
"""
import argparse
import datetime
import os
import re
import sys

TODAY = datetime.date.today().isoformat()

# --- regexes (compiled once) -------------------------------------------------
RE_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)
RE_LINE_COMMENT = re.compile(r"//[^\n]*")
RE_STRING = re.compile(r"'(?:[^'\\]|\\.)*'")

RE_PRIMARY = re.compile(
    r"\b(?P<access>global|public|private|protected)?\s*"
    r"(?P<sharing1>with sharing|without sharing|inherited sharing)?\s*"
    r"(?P<vmod>virtual|abstract)?\s*"
    r"(?P<sharing2>with sharing|without sharing|inherited sharing)?\s*"
    r"(?P<kind>class|interface|enum)\s+(?P<name>\w+)"
    r"(?:\s+extends\s+(?P<ext>[\w.<>, ]+?))?"
    r"(?:\s+implements\s+(?P<impl>[\w.<>, ]+?))?\s*\{",
    re.I,
)
RE_TYPE_DECL = re.compile(r"\b(?:class|interface|enum)\s+(\w+)", re.I)
RE_METHOD = re.compile(
    r"\b(?P<acc>global|public|private|protected)\s+"
    r"(?P<mods>(?:static|override|virtual|abstract|final|transient|webservice|testmethod)\s+)*"
    r"(?P<ret>[\w<>,.\[\]]+(?:\s*<[^>]*>)?[\w\[\]]*)\s+"
    r"(?P<name>\w+)\s*\((?P<args>[^)]*)\)\s*(?:\{|;)",
    re.I,
)
RE_SOQL = re.compile(r"\[\s*(?:SELECT|FIND)\b.*?\]", re.I | re.S)
RE_FROM = re.compile(r"\bFROM\s+([A-Za-z][\w.]*)", re.I)
RE_RETURNING = re.compile(r"\bRETURNING\s+([A-Za-z][\w.]*)", re.I)
RE_DML = re.compile(r"\b(insert|update|upsert|delete|undelete|merge)\b\s+[\w(]", re.I)
RE_DB = re.compile(
    r"\bDatabase\.(insert|update|upsert|delete|undelete|merge)\b", re.I
)
RE_ANNOT = re.compile(r"@(\w+)")
# Custom sObject suffixes only; __r is a relationship, not an object, so it is excluded.
RE_CUSTOM_OBJ = re.compile(r"\b([A-Za-z]\w*__(?:c|mdt|e|x|b|Share|History))\b")
RE_IDENT = re.compile(r"\b[A-Za-z_]\w*\b")
RE_TRIGGER = re.compile(
    r"\btrigger\s+(?P<name>\w+)\s+on\s+(?P<obj>\w+)\s*\((?P<events>[^)]*)\)", re.I
)
RE_CREATED = re.compile(r"Created by\s+(\S+)\s+on\s+([\d/.\-]+)", re.I)

STD_OBJECTS = {
    "Account", "Contact", "Case", "Lead", "Opportunity", "User", "Task", "Event",
    "Asset", "Product2", "Pricebook2", "PricebookEntry", "Order", "OrderItem",
    "Contract", "Quote", "QuoteLineItem", "Campaign", "CampaignMember", "Group",
    "ContentDocument", "ContentDocumentLink", "ContentVersion", "Attachment",
    "EmailMessage", "WorkOrder", "ServiceAppointment", "Entitlement",
}

DML_ORDER = ["insert", "update", "upsert", "delete", "undelete", "merge", "query"]


def strip_noise(src):
    s = RE_BLOCK_COMMENT.sub(" ", src)
    s = RE_LINE_COMMENT.sub(" ", s)
    s = RE_STRING.sub("''", s)
    return s


def yesc(s):
    return (s or "").replace('"', "'").replace("\n", " ").strip()


def is_test(name, annots, cleaned):
    if name.lower().endswith("test"):
        return True
    if any(a.lower() == "istest" for a in annots):
        return True
    return bool(re.search(r"\btestmethod\b", cleaned, re.I))


def derive_role(name, kind, impl, ext, annots):
    blob = (impl + " " + ext).lower()
    annl = {a.lower() for a in annots}
    n = name.lower()
    if "restresource" in annl:
        return "REST Service"
    if "batchable" in blob:
        return "Batch"
    if "schedulable" in blob:
        return "Scheduler"
    if "queueable" in blob:
        return "Queueable"
    if n.endswith(("triggerhandler", "triggerdelegate", "triggerhelper")):
        return "Trigger Handler"
    if "invocablemethod" in annl or "invocablevariable" in annl:
        return "Invocable"
    if "auraenabled" in annl or n.endswith(("controller", "ctrl")):
        return "Controller"
    if n.endswith("service"):
        return "Service"
    if n.endswith(("selector", "repository")):
        return "Selector"
    if n.endswith(("util", "utils", "utility", "helper")):
        return "Utility"
    if n.endswith(("wrapper", "dto", "model")):
        return "Wrapper/DTO"
    if "auraenabled" in annl:
        return "Controller"
    if kind == "interface":
        return "Interface"
    if kind == "enum":
        return "Enum"
    return "Class"


def domain_of(name):
    if "_" in name:
        return name.split("_", 1)[0]
    return "(no prefix)"


def parse_class(path, project):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()
    cleaned = strip_noise(raw)
    name = os.path.splitext(os.path.basename(path))[0]

    m = RE_PRIMARY.search(cleaned)
    kind = (m.group("kind").lower() if m else "class")
    decl_name = m.group("name") if m else name
    sharing = (m.group("sharing1") or m.group("sharing2") or "") if m else ""
    access = (m.group("access") or "") if m else ""
    vmod = (m.group("vmod") or "") if m else ""
    ext = (m.group("ext") or "").strip() if m else ""
    impl = (m.group("impl") or "").strip() if m else ""

    annots = sorted(set(RE_ANNOT.findall(cleaned)))
    inner = {n for n in RE_TYPE_DECL.findall(cleaned)}
    inner.discard(decl_name)

    methods = []
    for mm in RE_METHOD.finditer(cleaned):
        ret = mm.group("ret").strip()
        mname = mm.group("name")
        if ret.lower() in ("else", "return", "new", "if", "for", "while", "catch", "do"):
            continue
        if mname == decl_name and ret.lower() in ("class", "interface", "enum"):
            continue
        args = re.sub(r"\s+", " ", mm.group("args").strip())
        mods = " ".join((mm.group("acc"), (mm.group("mods") or "").strip())).strip()
        methods.append((mname, ret, args, mods))

    sobjects = set()
    soql_count = 0
    for q in RE_SOQL.finditer(cleaned):
        soql_count += 1
        seg = q.group(0)
        for obj in RE_FROM.findall(seg) + RE_RETURNING.findall(seg):
            sobjects.add(obj)
    for obj in RE_CUSTOM_OBJ.findall(cleaned):
        sobjects.add(obj)
    for std in STD_OBJECTS:
        if re.search(r"\b" + re.escape(std) + r"\b", cleaned):
            sobjects.add(std)

    dml = set()
    for d in RE_DML.findall(cleaned):
        dml.add(d.lower())
    for d in RE_DB.findall(cleaned):
        dml.add(d.lower())

    created_by = created_on = ""
    cm = RE_CREATED.search(raw)
    if cm:
        created_by, created_on = cm.group(1), cm.group(2)

    ids = set(RE_IDENT.findall(cleaned))

    return {
        "name": name,
        "decl_name": decl_name,
        "kind": kind,
        "access": access,
        "sharing": sharing,
        "vmod": vmod,
        "extends": ext,
        "implements": impl,
        "annots": annots,
        "inner": inner,
        "methods": methods,
        "sobjects": sorted(sobjects),
        "soql_count": soql_count,
        "dml": sorted(dml, key=lambda x: (DML_ORDER.index(x) if x in DML_ORDER else 99, x)),
        "created_by": created_by,
        "created_on": created_on,
        "ids": ids,
        "origin": path.replace("\\", "/"),
        "is_trigger": False,
        "project": project,
        "lines": raw.count("\n") + 1,
    }


def parse_trigger(path, project):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()
    cleaned = strip_noise(raw)
    name = os.path.splitext(os.path.basename(path))[0]
    tm = RE_TRIGGER.search(cleaned)
    obj = tm.group("obj") if tm else ""
    events = []
    if tm:
        events = [re.sub(r"\s+", " ", e.strip()) for e in tm.group("events").split(",") if e.strip()]
    ids = set(RE_IDENT.findall(cleaned))
    sobjects = set()
    if obj:
        sobjects.add(obj)
    for o in RE_CUSTOM_OBJ.findall(cleaned):
        sobjects.add(o)
    return {
        "name": name,
        "decl_name": name,
        "kind": "trigger",
        "object": obj,
        "events": events,
        "sobjects": sorted(sobjects),
        "ids": ids,
        "annots": [],
        "inner": set(),
        "origin": path.replace("\\", "/"),
        "is_trigger": True,
        "project": project,
        "lines": raw.count("\n") + 1,
        "role": "Trigger",
        "domain": domain_of(name),
    }


def list_files(d, ext):
    out = []
    for root, _dirs, files in os.walk(d):
        # never descend into SFDX/SF caches
        _dirs[:] = [x for x in _dirs if x not in (".sfdx", ".sf", "node_modules", ".git")]
        for fn in files:
            if fn.endswith(ext) and not fn.endswith("-meta.xml"):
                out.append(os.path.join(root, fn))
    return sorted(out)


def fm_list(items):
    return "[" + ", ".join(items) + "]" if items else "[]"


def fm_qlist(items):
    """YAML inline list of double-quoted strings (no backslashes in f-strings)."""
    return "[" + ", ".join('"' + i + '"' for i in items) + "]" if items else "[]"


def write_class_note(rec, outdir):
    name = rec["name"]
    role = rec["role"]
    domain = rec["domain"]
    fm = [
        "---",
        f'title: "{yesc(name)}"',
        "source_type: apex",
        f"origin: {rec['origin']}",
        f"ingested: {TODAY}",
        f'project: "{yesc(rec["project"])}"',
        f"apex_kind: {rec['kind']}",
        f'sharing: "{yesc(rec["sharing"] or "n/a")}"',
        f'role: "{role}"',
        f'domain: "{domain}"',
        f"sobjects: {fm_qlist(rec['sobjects'])}",
        f"invokes: {fm_qlist(rec['invokes'])}",
        f"tags: [research-source, apex, apex-{role.lower().replace('/', '-').replace(' ', '-')}]",
        "---",
        "",
    ]
    sig = " ".join(x for x in (rec["access"], rec["sharing"], rec["vmod"], rec["kind"], name) if x)
    body = [f"# {name}", "", f"`{sig.strip()}`", ""]
    facts = [("Role", role), ("Domain", domain)]
    if rec["extends"]:
        facts.append(("Extends", rec["extends"]))
    if rec["implements"]:
        facts.append(("Implements", rec["implements"]))
    if rec["annots"]:
        facts.append(("Annotations", ", ".join("@" + a for a in rec["annots"])))
    if rec["created_by"]:
        facts.append(("Authored", f"{rec['created_by']} ({rec['created_on']})"))
    facts.append(("Source lines", str(rec["lines"])))
    body += [f"- **{k}:** {v}" for k, v in facts] + [""]

    if rec["methods"]:
        body += ["## Methods", "", "| Method | Returns | Modifiers |", "| --- | --- | --- |"]
        for mname, ret, args, mods in rec["methods"]:
            sigm = f"`{mname}({args})`"
            body.append(f"| {sigm} | `{ret}` | {mods} |")
        body.append("")

    if rec["sobjects"]:
        body += ["## sObjects referenced", "", ", ".join(f"`{s}`" for s in rec["sobjects"]), ""]
    data_bits = []
    if rec["soql_count"]:
        data_bits.append(f"{rec['soql_count']} SOQL/SOSL queries")
    if rec["dml"]:
        data_bits.append("DML: " + ", ".join(rec["dml"]))
    if data_bits:
        body += ["## Data operations", "", "; ".join(data_bits), ""]

    if rec["invokes"]:
        body += ["## Invokes", "", ", ".join(f"[[{c}]]" for c in rec["invokes"]), ""]
    if rec["invoked_by"]:
        body += ["## Invoked by", "", ", ".join(f"[[{c}]]" for c in rec["invoked_by"]), ""]

    content = "\n".join(fm) + "\n".join(body).rstrip() + "\n"
    with open(os.path.join(outdir, f"{name}.md"), "w", encoding="utf-8") as f:
        f.write(content)


def write_trigger_note(rec, outdir):
    name = rec["name"]
    fm = [
        "---",
        f'title: "{yesc(name)}"',
        "source_type: apex",
        f"origin: {rec['origin']}",
        f"ingested: {TODAY}",
        f'project: "{yesc(rec["project"])}"',
        "apex_kind: trigger",
        'role: "Trigger"',
        f'domain: "{rec["domain"]}"',
        f'object: "{rec["object"]}"',
        f"sobjects: {fm_qlist(rec['sobjects'])}",
        f"invokes: {fm_qlist(rec['invokes'])}",
        "tags: [research-source, apex, apex-trigger]",
        "---",
        "",
    ]
    body = [f"# {name}", "", f"`trigger {name} on {rec['object']}`", ""]
    body += [f"- **Object:** `{rec['object']}`"]
    if rec["events"]:
        body.append(f"- **Events:** {', '.join(rec['events'])}")
    body.append(f"- **Source lines:** {rec['lines']}")
    body.append("")
    if rec["invokes"]:
        body += ["## Invokes", "", ", ".join(f"[[{c}]]" for c in rec["invokes"]), ""]
    content = "\n".join(fm) + "\n".join(body).rstrip() + "\n"
    with open(os.path.join(outdir, f"{name}.md"), "w", encoding="utf-8") as f:
        f.write(content)


def write_cluster_notes(records, clusters_dir, project):
    by_domain = {}
    for r in records:
        by_domain.setdefault(r["domain"], []).append(r)
    written = 0
    for domain, members in sorted(by_domain.items()):
        if len(members) < 2 or domain == "(no prefix)":
            continue
        safe = domain.replace("/", "-")
        by_role = {}
        objs = set()
        for r in members:
            by_role.setdefault(r["role"], []).append(r["name"])
            objs.update(r["sobjects"])
        fm = [
            "---",
            f'title: "{safe} (Apex domain)"',
            "source_type: apex-cluster",
            f"ingested: {TODAY}",
            f'project: "{yesc(project)}"',
            f"member_count: {len(members)}",
            "tags: [research-source, apex, apex-cluster]",
            "---",
            "",
        ]
        body = [f"# {safe} - Apex domain", "",
                f"{len(members)} classes/triggers sharing the `{domain}` prefix.", ""]
        for role in sorted(by_role):
            body += [f"## {role}", "", ", ".join(f"[[{n}]]" for n in sorted(by_role[role])), ""]
        if objs:
            body += ["## sObjects touched across this domain", "",
                     ", ".join(f"`{o}`" for o in sorted(objs)), ""]
        with open(os.path.join(clusters_dir, f"{safe}.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(fm) + "\n".join(body).rstrip() + "\n")
        written += 1
    return written


def write_index(records, apex_dir, project):
    by_role, by_domain = {}, {}
    rest, batch, sched, triggers, invocable = [], [], [], [], []
    invoked_count = {}
    obj_usage = {}
    for r in records:
        by_role.setdefault(r["role"], []).append(r["name"])
        by_domain.setdefault(r["domain"], 0)
        by_domain[r["domain"]] += 1
        if r["role"] == "REST Service":
            rest.append(r["name"])
        elif r["role"] == "Batch":
            batch.append(r["name"])
        elif r["role"] == "Scheduler":
            sched.append(r["name"])
        elif r.get("is_trigger"):
            triggers.append((r["name"], r.get("object", "")))
        if r["role"] == "Invocable":
            invocable.append(r["name"])
        invoked_count[r["name"]] = len(r["invoked_by"])
        for o in r["sobjects"]:
            obj_usage[o] = obj_usage.get(o, 0) + 1

    top_referenced = sorted(invoked_count.items(), key=lambda kv: (-kv[1], kv[0]))[:25]
    top_objects = sorted(obj_usage.items(), key=lambda kv: (-kv[1], kv[0]))[:25]

    fm = [
        "---",
        f'title: "Apex Architecture Index - {yesc(project)}"',
        "source_type: apex-index",
        f"ingested: {TODAY}",
        f'project: "{yesc(project)}"',
        f"class_count: {sum(1 for r in records if not r.get('is_trigger'))}",
        f"trigger_count: {sum(1 for r in records if r.get('is_trigger'))}",
        "tags: [research-source, apex, apex-index]",
        "---",
        "",
    ]
    body = [f"# Apex Architecture Index - {project}", "",
            f"Structural index of {len(records)} ingested Apex artifacts "
            f"({sum(1 for r in records if not r.get('is_trigger'))} classes, "
            f"{sum(1 for r in records if r.get('is_trigger'))} triggers). "
            "Test classes excluded unless noted.", ""]

    body += ["## By role", "", "| Role | Count |", "| --- | --- |"]
    for role in sorted(by_role, key=lambda r: (-len(by_role[r]), r)):
        body.append(f"| {role} | {len(by_role[role])} |")
    body.append("")

    body += ["## By domain (prefix)", "", "| Domain | Count |", "| --- | --- |"]
    for dom in sorted(by_domain, key=lambda d: (-by_domain[d], d)):
        link = f"[[{dom.replace('/', '-')}]]" if by_domain[dom] >= 2 and dom != "(no prefix)" else dom
        body.append(f"| {link} | {by_domain[dom]} |")
    body.append("")

    body += ["## Integration & async surface", ""]
    for label, items in [("REST services", sorted(rest)), ("Invocable (Flow) classes", sorted(invocable)),
                         ("Batch jobs", sorted(batch)), ("Schedulers", sorted(sched))]:
        if items:
            body += [f"### {label}", "", ", ".join(f"[[{n}]]" for n in items), ""]
    if triggers:
        body += ["### Triggers", "", "| Trigger | Object |", "| --- | --- |"]
        for n, obj in sorted(triggers):
            body.append(f"| [[{n}]] | `{obj}` |")
        body.append("")

    body += ["## Most-referenced classes (by inbound dependencies)", "",
             "| Class | Invoked by |", "| --- | --- |"]
    for n, c in top_referenced:
        if c:
            body.append(f"| [[{n}]] | {c} |")
    body.append("")

    body += ["## Most-touched sObjects", "", "| sObject | Classes referencing |", "| --- | --- |"]
    for o, c in top_objects:
        body.append(f"| `{o}` | {c} |")
    body.append("")

    with open(os.path.join(apex_dir, "_Apex Architecture Index.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(fm) + "\n".join(body).rstrip() + "\n")


def main():
    ap = argparse.ArgumentParser(description="Convert an Apex codebase to research notes.")
    ap.add_argument("--classes", required=True, help="Apex classes directory")
    ap.add_argument("--triggers", help="Apex triggers directory (optional)")
    ap.add_argument("--out", help="Output root (the project's Sources folder)")
    ap.add_argument("--project", default="Project", help="Research project name")
    ap.add_argument("--include-tests", action="store_true", help="Include *Test / @isTest classes")
    ap.add_argument("--limit", type=int, default=0, help="Parse at most N classes (testing)")
    ap.add_argument("--dry-run", action="store_true", help="Report stats only; write nothing")
    args = ap.parse_args()

    if not args.dry_run and not args.out:
        print("error: --out is required unless --dry-run", file=sys.stderr)
        return 2

    cls_files = list_files(args.classes, ".cls")
    if args.limit:
        cls_files = cls_files[: args.limit]
    trg_files = list_files(args.triggers, ".trigger") if args.triggers else []

    records = []
    skipped_tests = 0
    for p in cls_files:
        try:
            rec = parse_class(p, args.project)
        except Exception as e:  # never let one bad file abort the run
            print(f"warn: failed to parse {p}: {e}", file=sys.stderr)
            continue
        cleaned_for_test = strip_noise(open(p, encoding="utf-8", errors="replace").read())
        if not args.include_tests and is_test(rec["name"], rec["annots"], cleaned_for_test):
            skipped_tests += 1
            continue
        rec["role"] = derive_role(rec["name"], rec["kind"], rec["implements"],
                                  rec["extends"], rec["annots"])
        rec["domain"] = domain_of(rec["name"])
        records.append(rec)

    for p in trg_files:
        try:
            records.append(parse_trigger(p, args.project))
        except Exception as e:
            print(f"warn: failed to parse {p}: {e}", file=sys.stderr)

    # second pass: dependency graph over the known symbol universe
    known = {r["name"] for r in records}
    for r in records:
        deps = (r["ids"] & known) - {r["name"]} - r.get("inner", set())
        r["invokes"] = sorted(deps)
    inbound = {r["name"]: set() for r in records}
    for r in records:
        for d in r["invokes"]:
            if d in inbound:
                inbound[d].add(r["name"])
    for r in records:
        r["invoked_by"] = sorted(inbound[r["name"]])

    n_cls = sum(1 for r in records if not r.get("is_trigger"))
    n_trg = sum(1 for r in records if r.get("is_trigger"))
    if args.dry_run:
        roles = {}
        for r in records:
            roles[r["role"]] = roles.get(r["role"], 0) + 1
        print(f"DRY RUN: {n_cls} classes + {n_trg} triggers would be written "
              f"({skipped_tests} test classes skipped).")
        print("Roles: " + ", ".join(f"{k}={v}" for k, v in sorted(roles.items(), key=lambda kv: -kv[1])))
        return 0

    apex_dir = os.path.join(args.out, "Apex")
    classes_dir = os.path.join(apex_dir, "Classes")
    triggers_dir = os.path.join(apex_dir, "Triggers")
    clusters_dir = os.path.join(apex_dir, "Clusters")
    for d in (classes_dir, triggers_dir, clusters_dir):
        os.makedirs(d, exist_ok=True)

    for r in records:
        if r.get("is_trigger"):
            write_trigger_note(r, triggers_dir)
        else:
            write_class_note(r, classes_dir)
    n_clusters = write_cluster_notes(records, clusters_dir, args.project)
    write_index(records, apex_dir, args.project)

    print(f"Wrote {n_cls} class notes, {n_trg} trigger notes, {n_clusters} cluster notes, "
          f"and 1 architecture index to {apex_dir} ({skipped_tests} test classes skipped).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
