"""PAN validation and holder-type detection.

The 4th character of a PAN encodes the holder type. The journey uses it to
attach the right segment pack automatically (Step 0 of the design).
"""
import re

PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")

HOLDER_TYPES = {
    "P": ("Individual", "individual"),
    "H": ("Hindu Undivided Family (HUF)", "huf"),
    "C": ("Company", "corporate"),
    "F": ("Firm / LLP", "partnership"),
    "T": ("Trust", "trust"),
    "A": ("Association of Persons (AOP)", "other_entity"),
    "B": ("Body of Individuals (BOI)", "other_entity"),
    "G": ("Government", "other_entity"),
    "J": ("Artificial Juridical Person", "other_entity"),
    "L": ("Local Authority", "other_entity"),
}


def validate_pan(pan: str) -> dict:
    """Return format validity, holder type label and segment key."""
    pan = (pan or "").strip().upper()
    if not PAN_RE.match(pan):
        return {"valid": False, "pan": pan,
                "error": "PAN must be 10 characters: 5 letters, 4 digits, 1 letter (e.g. ABCPE1234F)."}
    code = pan[3]
    if code not in HOLDER_TYPES:
        return {"valid": False, "pan": pan, "error": f"4th character '{code}' is not a valid PAN holder type."}
    label, segment = HOLDER_TYPES[code]
    return {"valid": True, "pan": pan, "holder_code": code, "holder_label": label, "segment": segment}
