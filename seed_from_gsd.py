"""
Parsea GSD_MASTER.md y crea tareas pendientes en Maddox Scheduler via API.
Uso: python seed_from_gsd.py [API_BASE_URL]
Default: http://localhost:8000
"""

import re
import sys
import httpx
from pathlib import Path

API_BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
GSD_PATH = Path(__file__).parent.parent.parent / "GSD_MASTER.md"

# Mapeo de keywords en encabezados → nombre canónico de proyecto
PROJECT_MAP = {
    "umbra": "Umbra Performance",
    "tqq": "Soma Space Ops",
    "te quiero querétaro": "Soma Space Ops",
    "electric crayon": "Soma Space Ops",
    "teotlaneztli": "Soma Space Ops",
    "amae": "Soma Space Ops",
    "schwan": "Soma Space Ops",
    "phil": "Phil's Painting",
    "soma website": "Soma Space Ops",
    "soma agent": "SomaAgentBot",
    "fire-hire": "Fire-Hire",
    "firehire": "Fire-Hire",
    "ekho engine": "Ekho Engine",
    "skill builders": "Skill Builders ABA",
    "chimney chimp": "Chimney Chimp",
    "bespo": "Bespo Watches",
    "revolver": "Revolver Garage",
    "phoenix": "Soma Space Ops",
    "arganika": "Arganika Tree",
    "kdm": "KDM Tecnologías",
    "maalob": "Maalob",
    "ma'alob": "Maalob",
    "web-raiz": "web-raiz",
    "outreach": "Soma Space Ops",
    "maddox dashboard": "Personal",
    "gsd task": "Personal",
    "financial": "Personal",
    "system maintenance": "Personal",
    "infrastructure": "Personal",
    "n8n": "Personal",
}

# Prioridad por proyecto
PROJECT_PRIORITY = {
    "Skill Builders ABA": 5,
    "Chimney Chimp": 4,
    "Bespo Watches": 3,
    "KDM Tecnologías": 5,
    "Fire-Hire": 4,
    "Maalob": 4,
    "Arganika Tree": 4,
    "Umbra Performance": 3,
    "SomaAgentBot": 2,
    "Soma Space Ops": 3,
    "Phil's Painting": 3,
    "Revolver Garage": 2,
    "web-raiz": 3,
    "Ekho Engine": 3,
    "Personal": 1,
}


def detect_project(section_stack: list[str]) -> str:
    combined = " ".join(section_stack).lower()
    for keyword, project in PROJECT_MAP.items():
        if keyword in combined:
            return project
    return "Personal"


def parse_gsd(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    tasks = []
    section_stack = []

    for line in lines:
        # Track section headers
        header_match = re.match(r"^(#{1,4})\s+(.+)", line)
        if header_match:
            level = len(header_match.group(1))
            title = header_match.group(2).strip()
            # Trim stack to current level
            section_stack = section_stack[: level - 1]
            section_stack.append(title)
            continue

        # Match pending tasks: - [ ] **Title** — notes
        task_match = re.match(r"^\s*-\s+\[\s\]\s+\*?\*?(.+?)\*?\*?\s*(?:—\s*(.+))?$", line)
        if task_match:
            raw_title = task_match.group(1).strip()
            notes = task_match.group(2).strip() if task_match.group(2) else None

            # Clean markdown bold from title
            title = re.sub(r"\*\*(.+?)\*\*", r"\1", raw_title).strip()
            # Remove inline links [text](url)
            title = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", title)

            project = detect_project(section_stack)
            priority = PROJECT_PRIORITY.get(project, 3)

            tasks.append({
                "title": title,
                "project": project,
                "status": "todo",
                "priority": priority,
                "notes": notes,
            })

    return tasks


def main():
    print(f"Leyendo {GSD_PATH}...")
    tasks = parse_gsd(GSD_PATH)
    print(f"Encontradas {len(tasks)} tareas pendientes.\n")

    created = 0
    failed = 0

    with httpx.Client(base_url=API_BASE, timeout=10) as client:
        for task in tasks:
            try:
                r = client.post("/api/tasks", json=task)
                r.raise_for_status()
                print(f"  ✓ [{task['project']}] {task['title'][:60]}")
                created += 1
            except Exception as e:
                print(f"  ✗ Error: {task['title'][:40]} — {e}")
                failed += 1

    print(f"\nDone: {created} creadas, {failed} fallidas.")


if __name__ == "__main__":
    main()
