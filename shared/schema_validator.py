"""Validate cross-file type references in data/*.yaml files."""
from pathlib import Path
from typing import Any

import yaml

DATA_DIR: Path = Path(__file__).parent.parent / "data"


def load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML file."""
    with open(path) as f:
        return yaml.safe_load(f) or {}


def get_nested(data: dict[str, Any], path: str) -> set[str]:
    """Extract values at path. Returns set of strings found."""
    if not path or data is None:
        return set()
    parts: list[str] = path.replace("[*]", ".*").split(".")
    return _get_nested_recursive(data, parts)


def _get_nested_recursive(data: Any, parts: list[str]) -> set[str]:
    """Recursively extract values."""
    if not parts:
        if isinstance(data, str):
            return {data}
        if isinstance(data, list):
            return {x for x in data if isinstance(x, str)}
        return set()
    part: str = parts[0]
    rest: list[str] = parts[1:]
    if part == "*":
        if isinstance(data, dict):
            result: set[str] = set()
            for v in data.values():
                result |= _get_nested_recursive(v, rest)
            return result
        if isinstance(data, list):
            result = set()
            for v in data:
                result |= _get_nested_recursive(v, rest)
            return result
        return set()
    if part == "keys":
        if isinstance(data, dict):
            return set(data.keys())
        return set()
    if isinstance(data, dict) and part in data:
        return _get_nested_recursive(data[part], rest)
    return set()


def collect_definitions(schema: dict[str, Any]) -> dict[str, set[str]]:
    """Collect all type definitions from data files."""
    definitions: dict[str, set[str]] = {}
    for file_key, file_schema in schema.items():
        if "defines" not in file_schema:
            continue
        type_name: str = file_schema["defines"]
        path: str = file_schema.get("path", "keys")
        if file_key == "genres":
            values: set[str] = set()
            for genre_file in (DATA_DIR / "genres").glob("*.yaml"):
                data: dict[str, Any] = load_yaml(genre_file)
                values |= get_nested(data, path)
        elif file_key == "cadences":
            data = load_yaml(DATA_DIR / "cadences.yaml")
            values = get_nested(data, "internal.keys") | get_nested(data, "final.keys")
        else:
            yaml_path: Path = DATA_DIR / f"{file_key}.yaml"
            if not yaml_path.exists():
                continue
            data = load_yaml(yaml_path)
            values = get_nested(data, path)
        definitions[type_name] = values
    return definitions


def get_valid_values(type_spec: str, definitions: dict[str, set[str]]) -> set[str]:
    """Get valid values for a type spec. Supports union types with '|'."""
    valid: set[str] = set()
    for type_name in type_spec.split("|"):
        valid |= definitions.get(type_name.strip(), set())
    return valid


def validate_references(schema: dict[str, Any], definitions: dict[str, set[str]]) -> list[str]:
    """Validate all references against definitions."""
    errors: list[str] = []
    for file_key, file_schema in schema.items():
        refs: dict[str, str] = file_schema.get("references", {})
        if not refs:
            continue
        if file_key == "genres":
            for genre_file in (DATA_DIR / "genres").glob("*.yaml"):
                data: dict[str, Any] = load_yaml(genre_file)
                for ref_path, type_spec in refs.items():
                    values: set[str] = get_nested(data, ref_path)
                    valid: set[str] = get_valid_values(type_spec, definitions)
                    for v in values:
                        if v and v not in valid:
                            errors.append(f"{genre_file.name}: {ref_path}={v!r} not in {type_spec}")
        else:
            yaml_path: Path = DATA_DIR / f"{file_key}.yaml"
            if not yaml_path.exists():
                continue
            data = load_yaml(yaml_path)
            for ref_path, type_spec in refs.items():
                values = get_nested(data, ref_path)
                valid = get_valid_values(type_spec, definitions)
                for v in values:
                    if v and v not in valid:
                        errors.append(f"{file_key}.yaml: {ref_path}={v!r} not in {type_spec}")
    return errors


def validate_schema() -> tuple[bool, list[str]]:
    """Validate all data files against schema. Returns (valid, errors)."""
    schema_path: Path = DATA_DIR / "schema.yaml"
    schema: dict[str, Any] = load_yaml(schema_path)
    definitions: dict[str, set[str]] = collect_definitions(schema)
    errors: list[str] = validate_references(schema, definitions)
    return len(errors) == 0, errors


if __name__ == "__main__":
    valid, errors = validate_schema()
    if valid:
        print("Schema validation passed.")
    else:
        print(f"Schema validation failed with {len(errors)} errors:")
        for e in errors:
            print(f"  - {e}")
