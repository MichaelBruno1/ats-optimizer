"""Unit tests for Skill Normalization service."""

from app.services.skill_normalization import normalize_skill, get_equivalent_skills


def test_normalize_skill_aliases() -> None:
    # Case 1: Exact alias match
    assert normalize_skill("Amazon Web Services").canonical == "AWS"
    assert normalize_skill("aws").canonical == "AWS"
    assert normalize_skill("AWS Cloud").canonical == "AWS"

    # Case 2: Database aliases
    assert normalize_skill("Postgres").canonical == "PostgreSQL"
    assert normalize_skill("postgresql").canonical == "PostgreSQL"
    assert normalize_skill("Postgre SQL").canonical == "PostgreSQL"

    # Case 3: Kubernetes aliases
    assert normalize_skill("k8s").canonical == "Kubernetes"
    assert normalize_skill("Kubernetes").canonical == "Kubernetes"

    # Case 4: Languages & Frameworks
    assert normalize_skill("python 3").canonical == "Python"
    assert normalize_skill("fastapi").canonical == "FastAPI"
    assert normalize_skill("react.js").canonical == "React"


def test_get_equivalent_skills() -> None:
    assert "Flask" in get_equivalent_skills("FastAPI")
    assert "MySQL" in get_equivalent_skills("PostgreSQL")
    assert "Google Cloud Platform" in get_equivalent_skills("AWS")
