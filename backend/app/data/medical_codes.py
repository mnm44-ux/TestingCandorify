"""Bundled offline medical-code dataset.

Used by the synthetic bill generator and by the translation engine's offline
fallback. These are common, publicly-known CPT/HCPCS codes with plain-English
descriptions and realistic typical charge ranges (USD). Values are illustrative
for a prototype using SYNTHETIC data only.
"""
from __future__ import annotations

# code -> {system, short (billing text), plain (patient-friendly), low, high}
MEDICAL_CODES: dict[str, dict] = {
    # Evaluation & management
    "99213": {"system": "CPT", "short": "OFFICE/OUTPATIENT VISIT EST",
              "plain": "Standard office visit with your doctor (established patient)",
              "low": 90, "high": 180},
    "99214": {"system": "CPT", "short": "OFFICE/OUTPATIENT VISIT EST",
              "plain": "Longer or more complex office visit (established patient)",
              "low": 130, "high": 260},
    "99284": {"system": "CPT", "short": "EMERGENCY DEPT VISIT",
              "plain": "Emergency room visit, moderately complex",
              "low": 400, "high": 900},
    "99285": {"system": "CPT", "short": "EMERGENCY DEPT VISIT HIGH",
              "plain": "Emergency room visit, high complexity",
              "low": 700, "high": 1600},
    # Labs
    "80053": {"system": "CPT", "short": "COMPREHENSIVE METABOLIC PANEL",
              "plain": "Blood test panel checking kidney, liver, sugar and electrolytes",
              "low": 25, "high": 90},
    "85025": {"system": "CPT", "short": "COMPLETE CBC W/AUTO DIFF WBC",
              "plain": "Complete blood count (checks red/white cells and platelets)",
              "low": 20, "high": 75},
    "80048": {"system": "CPT", "short": "BASIC METABOLIC PANEL",
              "plain": "Basic blood chemistry panel",
              "low": 20, "high": 70},
    "81001": {"system": "CPT", "short": "URINALYSIS AUTO W/SCOPE",
              "plain": "Urine test with microscope examination",
              "low": 10, "high": 45},
    # Imaging
    "71046": {"system": "CPT", "short": "CHEST X-RAY 2 VIEWS",
              "plain": "Chest X-ray, two views",
              "low": 100, "high": 320},
    "74177": {"system": "CPT", "short": "CT ABD & PELVIS W/CONTRAST",
              "plain": "CT scan of the abdomen and pelvis with contrast dye",
              "low": 800, "high": 2500},
    "70450": {"system": "CPT", "short": "CT HEAD/BRAIN W/O CONTRAST",
              "plain": "CT scan of the head/brain without contrast dye",
              "low": 500, "high": 1500},
    "72148": {"system": "CPT", "short": "MRI LUMBAR SPINE W/O CONTRAST",
              "plain": "MRI of the lower back without contrast dye",
              "low": 700, "high": 2200},
    # Procedures
    "36415": {"system": "CPT", "short": "ROUTINE VENIPUNCTURE",
              "plain": "Drawing blood from a vein for testing",
              "low": 8, "high": 35},
    "12001": {"system": "CPT", "short": "SIMPLE REPAIR WOUND",
              "plain": "Stitching a simple wound",
              "low": 150, "high": 500},
    "93000": {"system": "CPT", "short": "ELECTROCARDIOGRAM COMPLETE",
              "plain": "Electrocardiogram (EKG) heart tracing, complete",
              "low": 30, "high": 120},
    "96372": {"system": "CPT", "short": "THER/PROPH/DIAG INJ SC/IM",
              "plain": "Therapeutic injection given under the skin or into muscle",
              "low": 25, "high": 90},
    # HCPCS supplies/drugs
    "J1885": {"system": "HCPCS", "short": "KETOROLAC TROMETHAMINE INJ",
              "plain": "Ketorolac (Toradol) injection, per 15 mg — a pain reliever",
              "low": 5, "high": 30},
    "J2405": {"system": "HCPCS", "short": "ONDANSETRON HCL INJECTION",
              "plain": "Ondansetron (Zofran) injection — anti-nausea medication",
              "low": 5, "high": 25},
    "A9150": {"system": "HCPCS", "short": "NON-RX DRUGS",
              "plain": "Non-prescription (over-the-counter) drugs",
              "low": 3, "high": 20},
    "Q9967": {"system": "HCPCS", "short": "LOCM 300-399MG/ML IODINE",
              "plain": "Contrast dye used during imaging, per mL",
              "low": 2, "high": 12},
}


def all_codes() -> list[str]:
    return list(MEDICAL_CODES.keys())


def lookup(code: str) -> dict | None:
    return MEDICAL_CODES.get(code.strip().upper())
