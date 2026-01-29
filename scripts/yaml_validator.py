"""Validate cross-file type references in YAML files and report usages.

This validator ensures coherence among YAML configuration files by:
1. Checking that all referenced types exist in their defining files
2. Detecting orphaned YAML files not used by any Python module
3. Generating a yaml_usages.yaml report showing module dependencies

Note: 'yaml_types.yaml' defines the type system (not to be confused with
musical 'schemas' like do_re_mi, prinner, etc. in data/schemas.yaml).
"""
import ast
import re
from pathlib import Path
from typing import Any

import yaml


PROJECT_DIR: Path = Path(__file__).parent.parent
DATA_DIR: Path = PROJECT_DIR / "data"
OUTPUT_DIR: Path = PROJECT_DIR / "output"


def load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML file safely."""
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_all_yaml_files() -> list[Path]:
    """Get all YAML files in the project (data/, briefs/)."""
    yaml_files: list[Path] = []
    for directory in [DATA_DIR, PROJECT_DIR / "briefs", PROJECT_DIR / "motifs"]:
        if directory.exists():
            yaml_files.extend(directory.rglob("*.yaml"))
    return sorted(yaml_files)


def get_all_python_files() -> list[Path]:
    """Get all Python source files in the project."""
    python_files: list[Path] = []
    for directory in [PROJECT_DIR / "builder", PROJECT_DIR / "planner",
                      PROJECT_DIR / "shared", PROJECT_DIR / "scripts",
                      PROJECT_DIR / "motifs"]:
        if directory.exists():
            python_files.extend(directory.rglob("*.py"))
    return sorted(python_files)


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


def collect_definitions(type_spec: dict[str, Any]) -> dict[str, set[str]]:
    """Collect all type definitions from data files per yaml_types.yaml."""
    definitions: dict[str, set[str]] = {}
    for file_key, file_schema in type_spec.items():
        if "defines" not in file_schema:
            continue
        type_name: str = file_schema["defines"]
        path: str = file_schema.get("path", "keys")

        if file_key == "genres":
            values: set[str] = set()
            genres_dir = DATA_DIR / "genres"
            if genres_dir.exists():
                for genre_file in genres_dir.glob("*.yaml"):
                    if genre_file.name.startswith("_"):
                        continue
                    data: dict[str, Any] = load_yaml(genre_file)
                    values |= get_nested(data, path)
        elif file_key == "cadences":
            data = load_yaml(DATA_DIR / "cadences" / "cadences.yaml")
            values = get_nested(data, "internal.keys") | get_nested(data, "final.keys")
        elif file_key == "treatments":
            data = load_yaml(DATA_DIR / "treatments" / "treatments.yaml")
            values = get_nested(data, path)
        else:
            yaml_path: Path = DATA_DIR / f"{file_key}.yaml"
            if not yaml_path.exists():
                continue
            data = load_yaml(yaml_path)
            values = get_nested(data, path)
        definitions[type_name] = values
    return definitions


def get_valid_values(type_spec_str: str, definitions: dict[str, set[str]]) -> set[str]:
    """Get valid values for a type spec. Supports union types with '|'."""
    valid: set[str] = set()
    for type_name in type_spec_str.split("|"):
        valid |= definitions.get(type_name.strip(), set())
    return valid


def validate_references(type_spec: dict[str, Any], definitions: dict[str, set[str]]) -> list[str]:
    """Validate all references against definitions."""
    errors: list[str] = []
    for file_key, file_schema in type_spec.items():
        refs: dict[str, str] = file_schema.get("references", {})
        if not refs:
            continue

        if file_key == "genres":
            genres_dir = DATA_DIR / "genres"
            if genres_dir.exists():
                for genre_file in genres_dir.glob("*.yaml"):
                    if genre_file.name.startswith("_"):
                        continue
                    data: dict[str, Any] = load_yaml(genre_file)
                    for ref_path, type_spec_str in refs.items():
                        values: set[str] = get_nested(data, ref_path)
                        valid: set[str] = get_valid_values(type_spec_str, definitions)
                        for v in values:
                            if v and v not in valid:
                                errors.append(
                                    f"{genre_file.relative_to(PROJECT_DIR)}: "
                                    f"{ref_path}={v!r} not in {type_spec_str}"
                                )
        else:
            yaml_path: Path = DATA_DIR / f"{file_key}.yaml"
            if not yaml_path.exists():
                continue
            data = load_yaml(yaml_path)
            for ref_path, type_spec_str in refs.items():
                values = get_nested(data, ref_path)
                valid = get_valid_values(type_spec_str, definitions)
                for v in values:
                    if v and v not in valid:
                        errors.append(
                            f"{file_key}.yaml: {ref_path}={v!r} not in {type_spec_str}"
                        )
    return errors


def extract_yaml_references_from_python(py_file: Path) -> set[str]:
    """Extract YAML file references from a Python source file."""
    references: set[str] = set()
    try:
        content: str = py_file.read_text(encoding="utf-8")
    except Exception:
        return references

    # Pattern 1: String literals containing .yaml
    yaml_pattern = re.compile(r'["\']([^"\']*\.yaml)["\']')
    for match in yaml_pattern.finditer(content):
        yaml_ref: str = match.group(1)
        references.add(yaml_ref)

    # Pattern 2: Path constructions like DATA_DIR / "foo" / "bar.yaml"
    path_pattern = re.compile(r'(?:DATA_DIR|PROJECT_DIR)\s*/\s*["\']([^"\']+)["\'](?:\s*/\s*["\']([^"\']+)["\'])*')
    for match in path_pattern.finditer(content):
        groups = [g for g in match.groups() if g]
        if groups:
            full_path = "/".join(groups)
            if full_path.endswith(".yaml") or any(g.endswith(".yaml") for g in groups):
                references.add(full_path)

    # Pattern 3: f-strings with .yaml
    fstring_pattern = re.compile(r'f["\'][^"\']*\.yaml[^"\']*["\']')
    for match in fstring_pattern.finditer(content):
        # Mark as dynamic reference
        references.add("<dynamic>.yaml")

    return references


def build_yaml_usages() -> dict[str, list[str]]:
    """Build mapping of YAML files to Python modules that use them."""
    usages: dict[str, list[str]] = {}
    py_files: list[Path] = get_all_python_files()

    for py_file in py_files:
        refs: set[str] = extract_yaml_references_from_python(py_file)
        module_name: str = str(py_file.relative_to(PROJECT_DIR)).replace("\\", "/").replace(".py", "")
        for ref in refs:
            if ref not in usages:
                usages[ref] = []
            usages[ref].append(module_name)

    # Sort the lists
    for key in usages:
        usages[key] = sorted(usages[key])

    return dict(sorted(usages.items()))


def find_orphaned_yaml_files(usages: dict[str, list[str]]) -> list[Path]:
    """Find YAML files not referenced by any Python module."""
    all_yaml: list[Path] = get_all_yaml_files()
    referenced: set[str] = set()

    # Normalize all references
    for ref in usages.keys():
        if ref == "<dynamic>.yaml":
            continue
        # Handle various path formats
        normalized = ref.replace("\\", "/").lstrip("/")
        referenced.add(normalized)
        # Also add just the filename
        referenced.add(Path(normalized).name)
        # And the relative path from data/
        if "/" in normalized:
            referenced.add(normalized.split("/", 1)[-1] if not normalized.startswith("data/") else normalized)

    # Data files are loaded dynamically via f-strings like f"{name}.yaml"
    # Mark data subdirectory files as referenced if the pattern exists
    has_dynamic_refs: bool = any("{" in ref for ref in usages.keys())

    orphaned: list[Path] = []
    for yaml_file in all_yaml:
        rel_path: str = str(yaml_file.relative_to(PROJECT_DIR)).replace("\\", "/")
        filename: str = yaml_file.name

        # Skip special files
        if filename.startswith("_"):
            continue
        if "briefs" in rel_path:
            continue  # Briefs are user data, not code dependencies

        # Data files in standard directories are dynamically loaded
        # They're not orphaned if the loader uses dynamic paths
        if has_dynamic_refs and rel_path.startswith("data/"):
            data_subdir = rel_path.split("/")[1] if "/" in rel_path else ""
            if data_subdir in ("forms", "genres"):
                continue  # These are loaded dynamically by config_loader.py

        # Check if referenced
        is_referenced: bool = (
            filename in referenced or
            rel_path in referenced or
            rel_path.replace("data/", "") in referenced
        )
        if not is_referenced:
            orphaned.append(yaml_file)

    return orphaned


def validate_yaml_syntax() -> list[str]:
    """Validate that all YAML files have valid syntax."""
    errors: list[str] = []
    for yaml_file in get_all_yaml_files():
        try:
            load_yaml(yaml_file)
        except yaml.YAMLError as e:
            rel_path: str = str(yaml_file.relative_to(PROJECT_DIR))
            errors.append(f"{rel_path}: YAML syntax error - {e}")
    return errors


def validate_required_fields() -> list[str]:
    """Validate that required fields exist in key configuration files."""
    errors: list[str] = []

    # Check genre files have required fields
    required_genre_fields = ["name", "voices", "form", "metre"]
    genres_dir = DATA_DIR / "genres"
    if genres_dir.exists():
        for genre_file in genres_dir.glob("*.yaml"):
            if genre_file.name.startswith("_"):
                continue
            data = load_yaml(genre_file)
            for field in required_genre_fields:
                if field not in data:
                    rel_path = str(genre_file.relative_to(PROJECT_DIR))
                    errors.append(f"{rel_path}: missing required field '{field}'")

    # Check form files have required fields (in data/forms/)
    required_form_fields = ["name"]
    forms_dir = DATA_DIR / "forms"
    if forms_dir.exists():
        for form_file in forms_dir.glob("*.yaml"):
            data = load_yaml(form_file)
            for field in required_form_fields:
                if field not in data:
                    rel_path = str(form_file.relative_to(PROJECT_DIR))
                    errors.append(f"{rel_path}: missing required field '{field}'")

    return errors


def get_schema_stages(schema_name: str, schemas: dict[str, Any]) -> int:
    """Get number of stages (bars) a schema occupies."""
    if schema_name not in schemas:
        return 1
    schema = schemas[schema_name]
    if schema.get("sequential"):
        segments = schema.get("segments", [2])
        if isinstance(segments, list):
            return max(segments)
        return segments
    soprano_degrees = schema.get("soprano_degrees", [])
    return len(soprano_degrees) if soprano_degrees else 1


def validate_genre_sections() -> list[str]:
    """Validate genre sections have non-empty schema_sequence."""
    errors: list[str] = []
    genres_dir = DATA_DIR / "genres"
    schemas_path = DATA_DIR / "schemas" / "schemas.yaml"
    if not genres_dir.exists():
        return errors
    schemas: dict[str, Any] = load_yaml(schemas_path) if schemas_path.exists() else {}
    for genre_file in genres_dir.glob("*.yaml"):
        if genre_file.name.startswith("_"):
            continue
        rel_path = str(genre_file.relative_to(PROJECT_DIR))
        data = load_yaml(genre_file)
        sections = data.get("sections", [])
        if not sections:
            continue
        for i, section in enumerate(sections):
            section_name = section.get("name", f"section_{i}")
            schema_sequence = section.get("schema_sequence", [])
            if not schema_sequence:
                errors.append(f"{rel_path}: section '{section_name}' has empty schema_sequence")
                continue
            for schema_name in schema_sequence:
                if schema_name != "episode" and schema_name not in schemas:
                    errors.append(
                        f"{rel_path}: section '{section_name}' references unknown schema '{schema_name}'"
                    )
    return errors


def validate_brief_files() -> list[str]:
    """Validate brief files don't have 'bars' field (sections define bars)."""
    errors: list[str] = []
    briefs_dir = PROJECT_DIR / "briefs"
    if not briefs_dir.exists():
        return errors
    for brief_file in briefs_dir.rglob("*.brief"):
        rel_path = str(brief_file.relative_to(PROJECT_DIR))
        data = load_yaml(brief_file)
        brief_section = data.get("brief", {})
        if "bars" in brief_section:
            errors.append(
                f"{rel_path}: brief has 'bars' field — remove it (bar count derived from schema_sequence)"
            )
    return errors


def write_yaml_usages(usages: dict[str, list[str]], orphaned: list[Path]) -> Path:
    """Write yaml_usages.yaml report to output directory."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path: Path = OUTPUT_DIR / "yaml_usages.yaml"

    report: dict[str, Any] = {
        "_meta": {
            "description": "YAML file usage report - which source modules use which YAML files",
            "generated_by": "shared/yaml_validator.py",
        },
        "usages": usages,
        "orphaned_files": [str(p.relative_to(PROJECT_DIR)) for p in orphaned],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(report, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    return output_path


def validate_all() -> tuple[bool, list[str], dict[str, list[str]], list[Path]]:
    """
    Run all validations.

    Returns:
        (all_valid, errors, usages, orphaned_files)
    """
    errors: list[str] = []

    # 1. Validate YAML syntax
    syntax_errors = validate_yaml_syntax()
    errors.extend(syntax_errors)

    # 2. Validate required fields
    field_errors = validate_required_fields()
    errors.extend(field_errors)

    # 3. Validate cross-references per yaml_types.yaml
    type_spec_path: Path = DATA_DIR / "yaml_types.yaml"
    if type_spec_path.exists():
        type_spec: dict[str, Any] = load_yaml(type_spec_path)
        definitions: dict[str, set[str]] = collect_definitions(type_spec)
        ref_errors = validate_references(type_spec, definitions)
        errors.extend(ref_errors)
    else:
        errors.append("data/yaml_types.yaml not found - cannot validate cross-references")

    # 4. Validate genre section structure and schema-bar coherence
    section_errors = validate_genre_sections()
    errors.extend(section_errors)

    # 5. Validate brief files don't conflict with genre sections
    brief_errors = validate_brief_files()
    errors.extend(brief_errors)

    # 6. Build usages map
    usages: dict[str, list[str]] = build_yaml_usages()

    # 7. Find orphaned files
    orphaned: list[Path] = find_orphaned_yaml_files(usages)

    return len(errors) == 0, errors, usages, orphaned


def main() -> None:
    """Run validation and generate report."""
    print("Validating YAML files...")
    print()

    valid, errors, usages, orphaned = validate_all()

    # Write usages report
    report_path = write_yaml_usages(usages, orphaned)
    print(f"Generated: {report_path.relative_to(PROJECT_DIR)}")
    print()

    # Report results
    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
        print()

    if orphaned:
        print(f"ORPHANED YAML FILES ({len(orphaned)}):")
        for p in orphaned:
            print(f"  - {p.relative_to(PROJECT_DIR)}")
        print()

    print(f"YAML files checked: {len(get_all_yaml_files())}")
    print(f"Python modules scanned: {len(get_all_python_files())}")
    print(f"Cross-reference usages tracked: {len(usages)}")
    print()

    if valid and not orphaned:
        print("Validation PASSED")
    elif valid:
        print("Validation PASSED (with orphaned files)")
    else:
        print("Validation FAILED")
        exit(1)


if __name__ == "__main__":
    main()
