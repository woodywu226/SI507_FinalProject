# Healthcare Provider Referral Network

**SI 507 – Final Project**  
**Author:** Woody Wu (`wuwoody`)  
**Target Grade:** A

---

## Data Sources

This project uses **real public data from the Centers for Medicare & Medicaid Services (CMS)**:

> **Medicare Physician & Other Practitioners – by Provider (CY 2022)**  
> https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners/medicare-physician-other-practitioners-by-provider  
> Public domain, no authentication required.

The dataset contains NPI, provider name, specialty, state, and total services billed to Medicare — over 1 million real physician records. The project downloads a filtered subset (Internal Medicine, Cardiology, Orthopedic Surgery, Neurology, Oncology, Primary Care) via the CMS public JSON API.

**Referral edges** are derived from shared-specialty + shared-state proximity, weighted by service volume. This mirrors the methodology used in published Medicare referral network research when the raw referral claims file requires a data-use agreement.

I also add a **synthetic fallback** (`generate_data.py`)  for offline use.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2a. Download REAL CMS data (requires internet — recommended)
python download_cms_data.py             # downloads ~1 000 real providers
python download_cms_data.py --limit 500 # smaller subset, faster

# 2b. OR generate synthetic data (offline fallback)
python generate_data.py

# 3a. Run the command-line interface
python cli.py

# 3b. Run the Streamlit web app
streamlit run app.py

# 4. Run the test suite
pytest test_referral_network.py -v
```

---

## Project Structure

```
healthcare_referral_network/
├── download_cms_data.py      # Downloads REAL CMS data via public API  <-- start here
├── generate_data.py          # Synthetic fallback (offline use)
├── models.py                 # Core OOP: Provider + ReferralNetwork classes
├── cli.py                    # Interactive command-line interface
├── app.py                    # Streamlit web application
├── test_referral_network.py  # pytest test suite (50+ tests)
├── requirements.txt
├── README.md
└── data/                     # Created by download script
    ├── providers.csv
    └── referrals.csv
```

---

## Graph Structure

| Element | Represents |
|---------|------------|
| **Node** | Individual healthcare provider (real NPI from CMS) |
| **Edge** | Directed referral relationship (A refers patients to B) |
| **Weight** | Referral count (derived from shared Medicare service volume) |

---

## Interaction Modes

| # | Mode | Description |
|---|------|-------------|
| 1 | **Search providers** | Filter by name, specialty, and/or region (state) |
| 2 | **Provider detail** | Full profile + top referral partners |
| 3 | **Top central** | Rank by degree / betweenness / in/out-degree centrality |
| 4 | **Referral path** | Highest-traffic path between two providers |
| 5 | **Specialty filter** | All edges from one specialty to another |
| 6 | **Network summary** | Aggregate stats, top corridors, specialty/region breakdown |

---

## Note on Referral Edge Derivation

The raw CMS Physician Referral file requires a formal CMS data-use agreement. This project derives edges from the public Physician & Other Practitioners file using shared-specialty + shared-state proximity weighted by service volume — a standard approach in Medicare referral network research (Barnett et al., Health Services Research, 2011).
