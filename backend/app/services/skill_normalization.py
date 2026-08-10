"""Skill Ontology and Normalization Service.

Normalizes skill variations, acronyms, and aliases into canonical forms.
Uses rules, regex, and taxonomy mapping BEFORE matching engine execution.
Does NOT rely exclusively on LLM calls.
"""

import re
from typing import NamedTuple


class NormalizedSkill(NamedTuple):
    original: str
    canonical: str
    category: str


# Canonical dictionary mapping aliases to standardized skills
SKILL_ALIASES: dict[str, str] = {
    # Cloud & DevOps
    "aws": "AWS",
    "amazon web services": "AWS",
    "aws cloud": "AWS",
    "k8s": "Kubernetes",
    "k8bs": "Kubernetes",
    "kubernetes": "Kubernetes",
    "docker": "Docker",
    "docker containers": "Docker",
    "gcp": "Google Cloud Platform",
    "google cloud": "Google Cloud Platform",
    "google cloud platform": "Google Cloud Platform",
    "azure": "Microsoft Azure",
    "microsoft azure": "Microsoft Azure",
    "ci/cd": "CI/CD",
    "continuous integration": "CI/CD",
    "continuous deployment": "CI/CD",
    "terraform": "Terraform",
    
    # Databases
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "postgre sql": "PostgreSQL",
    "postgre": "PostgreSQL",
    "mongo": "MongoDB",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "mysql": "MySQL",
    "mssql": "SQL Server",
    "sql server": "SQL Server",
    
    # Languages & Frameworks
    "python": "Python",
    "python 3": "Python",
    "python3": "Python",
    "fastapi": "FastAPI",
    "fast api": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "react": "React",
    "react.js": "React",
    "reactjs": "React",
    "node": "Node.js",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "golang": "Go",
    "go lang": "Go",
    "go": "Go",
    "java": "Java",
    "c#": "C#",
    ".net": ".NET",
    "dotnet": ".NET",
}

# Skill category taxonomy
SKILL_CATEGORIES: dict[str, str] = {
    "AWS": "cloud",
    "Kubernetes": "devops",
    "Docker": "devops",
    "Google Cloud Platform": "cloud",
    "Microsoft Azure": "cloud",
    "CI/CD": "devops",
    "Terraform": "devops",
    "PostgreSQL": "database",
    "MongoDB": "database",
    "Redis": "database",
    "MySQL": "database",
    "SQL Server": "database",
    "Python": "language",
    "FastAPI": "framework",
    "Flask": "framework",
    "Django": "framework",
    "React": "frontend",
    "Node.js": "backend",
    "JavaScript": "language",
    "TypeScript": "language",
    "Go": "language",
    "Java": "language",
    "C#": "language",
    ".NET": "framework",
}

# Equivalency map for partial match identification (e.g., Flask is equivalent/partial for FastAPI)
SKILL_EQUIVALENCIES: dict[str, list[str]] = {
    "FastAPI": ["Flask", "Django", "Bottle", "Tornado"],
    "PostgreSQL": ["MySQL", "MariaDB", "SQLite"],
    "React": ["Vue.js", "Angular", "Svelte"],
    "AWS": ["Google Cloud Platform", "Microsoft Azure"],
    "Kubernetes": ["Docker Swarm", "Amazon ECS"],
}


def normalize_skill(skill: str) -> NormalizedSkill:
    """Normalize a raw skill string to its canonical form and category.

    Args:
        skill: Raw input skill string (e.g. "Amazon AWS", "k8s", "postgres").

    Returns:
        NormalizedSkill object with original name, canonical name, and category.
    """
    cleaned = skill.strip().lower()
    # Remove excessive punctuation except + and #
    cleaned_key = re.sub(r"[^\w\s\+#/\.-]", "", cleaned)

    canonical = SKILL_ALIASES.get(cleaned_key) or SKILL_ALIASES.get(cleaned)

    if not canonical:
        # Title case standard words if no alias match
        words = skill.strip().split()
        canonical = " ".join(w.capitalize() if not w.isupper() else w for w in words)

    category = SKILL_CATEGORIES.get(canonical, "general")
    return NormalizedSkill(original=skill.strip(), canonical=canonical, category=category)


def get_equivalent_skills(canonical_skill: str) -> list[str]:
    """Return list of known equivalent or transferable skills."""
    return SKILL_EQUIVALENCIES.get(canonical_skill, [])
