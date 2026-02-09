from datasets import load_dataset
import re

def delatex(s):
    """Strip LaTeX markup to plain readable text."""
    s = s.replace("\\{", "{").replace("\\}", "}")
    s = s.replace("\\to", "→").replace("\\in", "∈")
    s = s.replace("\\leq", "≤").replace("\\geq", "≥")
    s = s.replace("\\neq", "≠").replace("\\approx", "≈")
    s = s.replace("\\infty", "∞").replace("\\emptyset", "∅")
    s = s.replace("\\cup", "∪").replace("\\cap", "∩")
    s = s.replace("\\subset", "⊂").replace("\\subseteq", "⊆")
    s = s.replace("\\times", "×").replace("\\cdot", "·")
    s = s.replace("\\ldots", "...").replace("\\cdots", "...")
    s = s.replace("\\log", "log").replace("\\max", "max").replace("\\min", "min")
    s = re.sub(r'\$([^$]+)\$', r'\1', s)       # strip inline $ ... $
    s = re.sub(r'\\text\{([^}]+)\}', r'\1', s)  # \text{foo} → foo
    s = re.sub(r'\\mathbb\{([^}]+)\}', r'\1', s)
    s = re.sub(r'\\mathrm\{([^}]+)\}', r'\1', s)
    s = re.sub(r'\^(\{[^}]+\})', r'^(\1)', s)   # superscripts
    s = re.sub(r'_(\{[^}]+\})', r'_(\1)', s)    # subscripts
    s = s.replace("{", "").replace("}", "")
    s = re.sub(r'\\[a-zA-Z]+', '', s)           # kill remaining commands
    s = re.sub(r'  +', ' ', s)                   # collapse whitespace
    return s.strip()

ds = load_dataset("cais/hle", split="test")

for row in ds:
    cat = (row.get("category") or row.get("raw_subject") or "").lower()
    if "computer" in cat or "artificial" in cat or "machine learning" in cat:
        print(delatex(row["question"]))
        print(f"Answer: {delatex(row['answer'])}")
        print("---")