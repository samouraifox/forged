"""Convert MITRE ATT&CK STIX JSON into chunker-friendly markdown strings."""
import json
from pathlib import Path

ATTACK_DIRS = [
    "enterprise-attack/attack-pattern",
    "ics-attack/attack-pattern",
    "mobile-attack/attack-pattern",
]

def stix_to_markdown(obj: dict) -> tuple[str, str] | None:
    """Return (rel_path, markdown) for an attack-pattern STIX object, or None."""
    if obj.get("type") != "attack-pattern":
        return None
    name = obj.get("name", "unknown")
    desc = obj.get("description", "").strip()
    ext_refs = obj.get("external_references", [])
    attack_id = next((r.get("external_id") for r in ext_refs if r.get("source_name") == "mitre-attack"), None)
    if not attack_id:
        return None
    phases = [p.get("phase_name", "") for p in obj.get("kill_chain_phases", [])]
    platforms = obj.get("x_mitre_platforms", [])
    detection = obj.get("x_mitre_detection", "").strip()

    md_lines = [f"# {attack_id}: {name}", ""]
    if phases:
        md_lines.append(f"**Kill chain phases:** {', '.join(phases)}")
    if platforms:
        md_lines.append(f"**Platforms:** {', '.join(platforms)}")
    md_lines.append("")
    if desc:
        md_lines += ["## Description", "", desc, ""]
    if detection:
        md_lines += ["## Detection", "", detection, ""]
    refs = [f"- {r.get('source_name')}: {r.get('url', r.get('external_id', ''))}" for r in ext_refs if r.get("url") or r.get("external_id")]
    if refs:
        md_lines += ["## References", "", *refs]
    return attack_id, "\n".join(md_lines)

def iter_mitre_markdown(root: Path):
    """Yield (rel_path, markdown_str) for each ATT&CK technique."""
    for sub in ATTACK_DIRS:
        d = root / sub
        if not d.exists():
            continue
        for jf in d.glob("*.json"):
            try:
                data = json.loads(jf.read_text(encoding="utf-8", errors="ignore"))
            except Exception:
                continue
            for obj in data.get("objects", []):
                res = stix_to_markdown(obj)
                if res:
                    attack_id, md = res
                    matrix = sub.split("/")[0]
                    yield f"{matrix}/{attack_id}.md", md

if __name__ == "__main__":
    import sys
    root = Path(sys.argv[1])
    n = 0
    for rel, md in iter_mitre_markdown(root):
        n += 1
        if n <= 2:
            print(f"--- {rel} ---")
            print(md[:400])
    print(f"\nTotal: {n} techniques")
