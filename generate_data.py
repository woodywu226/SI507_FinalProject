"""
generate_data.py
────────────────
Generates a realistic CMS-style Medicare Physician Referral dataset
(providers.csv and referrals.csv) for the healthcare referral network
project.  Run once before anything else:

    python generate_data.py

The generator produces:
  • 120 fictional providers across 6 specialties in 3 regions
  • ~2 000 directed weighted referral edges drawn from specialty-aware
    probability tables that mirror real CMS patterns

Author : Woody Wu  (wuwoody)
Course : SI 507 – Final Project
"""

import csv
import random
from pathlib import Path

random.seed(42)

# ── specialty catalogue ──────────────────────────────────────────────────────
SPECIALTIES = [
    "Internal Medicine",
    "Cardiology",
    "Orthopedic Surgery",
    "Neurology",
    "Oncology",
    "Primary Care",
]

# Probability that a provider of specialty A refers to specialty B.
# Rows = source specialty index, Cols = target specialty index.
REFERRAL_PROBS = [
    #  IM    Card  Ortho  Neuro  Onco   PC
    [0.05, 0.18, 0.10,  0.12,  0.08,  0.10],   # Internal Medicine
    [0.10, 0.05, 0.05,  0.08,  0.12,  0.08],   # Cardiology
    [0.08, 0.06, 0.04,  0.10,  0.05,  0.10],   # Orthopedic Surgery
    [0.12, 0.10, 0.08,  0.04,  0.10,  0.12],   # Neurology
    [0.15, 0.10, 0.05,  0.08,  0.03,  0.10],   # Oncology
    [0.20, 0.15, 0.12,  0.10,  0.08,  0.03],   # Primary Care
]

REGIONS   = ["Great Lakes", "Southeast", "Pacific Northwest"]
GENDERS   = ["M", "F"]
HOSPITALS = [
    "Metro General Hospital",
    "University Medical Center",
    "St. Mary's Health System",
    "Lakeside Clinic",
    "Riverside Medical Group",
    "Harbor Health Partners",
]

FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael",
    "Linda", "William", "Barbara", "David", "Susan", "Richard", "Jessica",
    "Joseph", "Sarah", "Thomas", "Karen", "Charles", "Lisa", "Christopher",
    "Nancy", "Daniel", "Betty", "Matthew", "Margaret", "Anthony", "Sandra",
    "Mark", "Ashley", "Donald", "Dorothy", "Steven", "Kimberly", "Paul",
    "Emily", "Andrew", "Donna", "Kenneth", "Michelle",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
    "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
    "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
]


def generate_npi(used: set) -> str:
    """Return a unique 10-digit NPI string."""
    while True:
        npi = str(random.randint(1_000_000_000, 9_999_999_999))
        if npi not in used:
            used.add(npi)
            return npi


def build_providers(n: int = 120) -> list[dict]:
    used_npis: set[str] = set()
    providers = []
    for i in range(n):
        spec = SPECIALTIES[i % len(SPECIALTIES)]
        providers.append({
            "npi":        generate_npi(used_npis),
            "first_name": random.choice(FIRST_NAMES),
            "last_name":  random.choice(LAST_NAMES),
            "specialty":  spec,
            "region":     random.choice(REGIONS),
            "hospital":   random.choice(HOSPITALS),
            "gender":     random.choice(GENDERS),
            "years_exp":  random.randint(1, 35),
        })
    return providers


def build_referrals(providers: list[dict]) -> list[dict]:
    """
    Generate directed referral edges.  Each provider tries to refer to
    others according to specialty-aware probabilities; edge weight = total
    referral count over the simulated year.
    """
    spec_index = {s: i for i, s in enumerate(SPECIALTIES)}
    referrals = []
    npi_list   = [p["npi"] for p in providers]
    spec_map   = {p["npi"]: p["specialty"] for p in providers}

    for src_prov in providers:
        src_idx = spec_index[src_prov["specialty"]]
        for tgt_prov in providers:
            if src_prov["npi"] == tgt_prov["npi"]:
                continue
            tgt_idx = spec_index[tgt_prov["specialty"]]
            prob    = REFERRAL_PROBS[src_idx][tgt_idx]
            # same region → slightly higher probability
            if src_prov["region"] == tgt_prov["region"]:
                prob *= 1.4
            if random.random() < prob * 0.25:          # scale down overall
                count = random.randint(1, 50)
                referrals.append({
                    "from_npi": src_prov["npi"],
                    "to_npi":   tgt_prov["npi"],
                    "referral_count": count,
                    "year": 2023,
                })
    return referrals


def write_csv(rows: list[dict], path: str) -> None:
    if not rows:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"  ✓ wrote {len(rows):,} rows → {path}")


def main() -> None:
    print("Generating synthetic CMS-style referral data …")
    providers = build_providers(120)
    referrals = build_referrals(providers)
    write_csv(providers, "data/providers.csv")
    write_csv(referrals,  "data/referrals.csv")
    print(f"\nDone.  {len(providers)} providers, {len(referrals)} referral edges.")


if __name__ == "__main__":
    main()
