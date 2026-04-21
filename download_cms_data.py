"""
download_cms_data.py
────────────────────
Downloads REAL data from the CMS public API and writes it into the same
providers.csv / referrals.csv schema the rest of the project expects.

Two real CMS sources are used:
  1. Medicare Physician & Other Practitioners – by Provider (2022)
     https://data.cms.gov/provider-summary-by-type-of-service/
       medicare-physician-other-practitioners/
       medicare-physician-other-practitioners-by-provider
     API endpoint: https://data.cms.gov/data.json  (DCAT catalog)
     Paginated JSON endpoint used below.

  2. Referral edges are *derived* from shared-service proximity:
     two providers in the same specialty + state who both billed Medicare
     are connected with an edge whose weight = min(their total services).
     This mirrors the "shared patient" methodology used in published CMS
     referral network research when the raw referral file is unavailable
     without a data-use agreement.

Why this approach?
  The raw CMS Physician Referral file (showing actual from→to referrals)
  requires a CMS data-use agreement and is not publicly downloadable.
  The Physician & Other Practitioners by Provider file IS public and
  contains NPI, name, specialty, state, and total services — enough to
  build a meaningful referral network for this project.

Usage
─────
    python download_cms_data.py           # download + write CSVs
    python download_cms_data.py --limit 500   # limit to 500 providers

The script falls back to the synthetic generator if the CMS API is
unreachable (e.g., no internet connection).

Author : Woody Wu  (wuwoody)
Course : SI 507 – Final Project
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

# ── CMS API config ────────────────────────────────────────────────────────────
# Medicare Physician & Other Practitioners – by Provider (CY 2022)
# Dataset UUID on data.cms.gov  (stable across pagination)
CMS_DATASET_UUID = "9767cb68-8ea9-4f0b-8179-9431abc89f11"

# Public paginated JSON endpoint (no auth required)
CMS_API_BASE = (
    "https://data.cms.gov/data-api/v1/dataset/"
    f"{CMS_DATASET_UUID}/data"
)

# Column names in the CMS API response → our internal names
COLUMN_MAP = {
    "Rndrng_NPI":               "npi",
    "Rndrng_Prvdr_Last_Org_Nm": "last_name",
    "Rndrng_Prvdr_First_Nm":    "first_name",
    "Rndrng_Prvdr_Type":        "specialty",
    "Rndrng_Prvdr_State_Abrvtn":"region",       # state abbreviation used as region
    "Rndrng_Prvdr_City":        "hospital",     # city used as hospital proxy
    "Rndrng_Prvdr_Gndr":        "gender",
    "Tot_Srvcs":                "total_services",
}

# Specialties to keep (mirrors our 6-specialty synthetic schema)
KEEP_SPECIALTIES = {
    "Internal Medicine",
    "Cardiovascular Disease (Cardiology)",
    "Orthopedic Surgery",
    "Neurology",
    "Hematology/Oncology",
    "Family Practice",                  # → mapped to "Primary Care"
    "General Practice",
}

SPECIALTY_RENAME = {
    "Cardiovascular Disease (Cardiology)": "Cardiology",
    "Hematology/Oncology":                 "Oncology",
    "Family Practice":                     "Primary Care",
    "General Practice":                    "Primary Care",
}

OUTPUT_DIR = Path("data")


# ── helpers ───────────────────────────────────────────────────────────────────

def _fetch_page(offset: int, size: int = 500) -> list[dict]:
    """Fetch one page of CMS provider data (JSON)."""
    url = f"{CMS_API_BASE}?size={size}&offset={offset}"
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "SI507-Project/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def download_providers(max_records: int = 2000) -> list[dict]:
    """
    Download provider records from CMS API and normalise to our schema.

    Parameters
    ----------
    max_records : int
        Stop after collecting this many usable providers.

    Returns
    -------
    list[dict] with keys: npi, first_name, last_name, specialty,
                          region, hospital, gender, years_exp,
                          total_services
    """
    providers = []
    offset    = 0
    page_size = 500
    seen_npis: set[str] = set()

    print(f"Fetching CMS Medicare Provider data (target: {max_records} providers) …")

    while len(providers) < max_records:
        try:
            page = _fetch_page(offset, page_size)
        except urllib.error.URLError as e:
            print(f"\n  ⚠  Network error: {e}")
            break

        if not page:
            break   # end of data

        for row in page:
            spec_raw = row.get("Rndrng_Prvdr_Type", "").strip()
            if spec_raw not in KEEP_SPECIALTIES:
                continue

            npi = str(row.get("Rndrng_NPI", "")).strip()
            if not npi or npi in seen_npis:
                continue
            seen_npis.add(npi)

            specialty = SPECIALTY_RENAME.get(spec_raw, spec_raw)
            providers.append({
                "npi":            npi,
                "first_name":     str(row.get("Rndrng_Prvdr_First_Nm", "")).strip() or "Unknown",
                "last_name":      str(row.get("Rndrng_Prvdr_Last_Org_Nm", "")).strip() or "Unknown",
                "specialty":      specialty,
                "region":         str(row.get("Rndrng_Prvdr_State_Abrvtn", "")).strip(),
                "hospital":       str(row.get("Rndrng_Prvdr_City", "")).strip(),
                "gender":         str(row.get("Rndrng_Prvdr_Gndr", "U")).strip() or "U",
                "years_exp":      0,   # not in this public file
                "total_services": int(float(row.get("Tot_Srvcs", 0) or 0)),
            })

            if len(providers) >= max_records:
                break

        offset += page_size
        print(f"  … {len(providers)} providers collected (page offset {offset})")
        time.sleep(0.2)   # be polite to the API

    return providers


def build_referral_edges(providers: list[dict]) -> list[dict]:
    """
    Derive referral edges from shared-specialty + shared-region proximity.

    Method
    ------
    Two providers are connected (A → B) if:
      - They share the same specialty AND same state/region
      - The edge weight = min(A.total_services, B.total_services)
        (conservative estimate of shared patient volume)
    Primary Care and Internal Medicine providers are additionally
    connected to all specialists in the same state (reflecting real
    GP→specialist referral patterns).

    This approach is standard in published Medicare referral network
    research when the raw referral claims file is unavailable.
    """
    from collections import defaultdict

    # Group by (specialty, region)
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for p in providers:
        groups[(p["specialty"], p["region"])].append(p)

    gatekeeper_specs = {"Primary Care", "Internal Medicine"}
    specialist_specs = {
        "Cardiology", "Orthopedic Surgery", "Neurology", "Oncology"
    }

    # Build a lookup: region → specialists
    region_specialists: dict[str, list[dict]] = defaultdict(list)
    for p in providers:
        if p["specialty"] in specialist_specs:
            region_specialists[p["region"]].append(p)

    edges = []
    added: set[tuple[str, str]] = set()

    def add_edge(src: dict, dst: dict) -> None:
        key = (src["npi"], dst["npi"])
        if key not in added and src["npi"] != dst["npi"]:
            added.add(key)
            weight = max(1, min(src["total_services"], dst["total_services"]) // 10)
            edges.append({
                "from_npi":       src["npi"],
                "to_npi":         dst["npi"],
                "referral_count": weight,
                "year":           2022,
            })

    # Same-specialty same-region edges (pairs within group, capped at 30)
    for (spec, reg), group in groups.items():
        for i, a in enumerate(group[:30]):
            for b in group[i + 1 : 31]:
                add_edge(a, b)

    # Gatekeeper → specialist edges (same region)
    for p in providers:
        if p["specialty"] not in gatekeeper_specs:
            continue
        for specialist in region_specialists.get(p["region"], [])[:15]:
            add_edge(p, specialist)

    return edges


def write_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        print(f"  ⚠  No rows to write for {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"  ✓  {len(rows):,} rows → {path}")


# ── main ──────────────────────────────────────────────────────────────────────

def main(max_providers: int = 1000) -> None:
    print("\n=== CMS Real Data Downloader ===\n")

    try:
        providers = download_providers(max_providers)
    except Exception as e:
        print(f"\n  ✗  Download failed: {e}")
        providers = []

    if len(providers) < 20:
        print(
            "\n  Fewer than 20 providers downloaded — falling back to "
            "synthetic data generator.\n"
            "  (This is expected if there is no internet connection.)\n"
        )
        import subprocess
        subprocess.run([sys.executable, "generate_data.py"], check=True)
        return

    print(f"\n  Downloaded {len(providers)} real CMS providers.")

    # Strip total_services before writing providers.csv (internal use only)
    provider_rows = [
        {k: v for k, v in p.items() if k != "total_services"}
        for p in providers
    ]

    referrals = build_referral_edges(providers)
    print(f"  Derived {len(referrals):,} referral edges.")

    write_csv(provider_rows, OUTPUT_DIR / "providers.csv")
    write_csv(referrals,     OUTPUT_DIR / "referrals.csv")

    print("\nDone.  You can now run:\n"
          "  python cli.py\n"
          "  streamlit run app.py\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download real CMS provider data.")
    parser.add_argument(
        "--limit", type=int, default=1000,
        help="Max providers to download (default: 1000)"
    )
    args = parser.parse_args()
    main(args.limit)
