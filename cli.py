"""
cli.py
──────
Command-line interface for the Healthcare Provider Referral Network.

Usage
─────
    python cli.py

The interactive menu exposes all six interaction modes:
  1. Search providers
  2. View provider detail
  3. Top-central providers
  4. Find referral path
  5. Filter referrals by specialty
  6. Network summary

Author : Woody Wu  (wuwoody)
Course : SI 507 – Final Project
"""

from __future__ import annotations

from models import ReferralNetwork, Provider


# ── helpers ──────────────────────────────────────────────────────────────────

DIVIDER = "─" * 60


def _sep(title: str = "") -> None:
    if title:
        print(f"\n{DIVIDER}")
        print(f"  {title}")
        print(DIVIDER)
    else:
        print(DIVIDER)


def _prompt(msg: str, default: str = "") -> str:
    val = input(f"  {msg}: ").strip()
    return val if val else default


def _pause() -> None:
    input("\n  [Enter to continue] ")


# ── mode handlers ─────────────────────────────────────────────────────────────

def mode_search(net: ReferralNetwork) -> None:
    """INTERACTION MODE 1 – Search for providers."""
    _sep("MODE 1 – Search Providers")
    query     = _prompt("Name (partial, or blank)", "")
    specialty = _prompt("Specialty (partial, or blank)", "")
    region    = _prompt("Region (partial, or blank)", "")

    results = net.search_provider(query, specialty, region)
    if not results:
        print("\n  No providers matched your query.")
    else:
        print(f"\n  Found {len(results)} provider(s):\n")
        for p in results:
            print(f"    {p.display_id}")
            print(f"      Region: {p.region}  |  Hospital: {p.hospital}  "
                  f"|  Exp: {p.years_exp} yrs")
    _pause()


def mode_detail(net: ReferralNetwork) -> None:
    """INTERACTION MODE 2 – View full provider profile."""
    _sep("MODE 2 – Provider Detail")
    npi = _prompt("Enter NPI")
    detail = net.get_provider_detail(npi)
    if detail is None:
        print(f"\n  NPI {npi!r} not found in network.")
    else:
        p = detail["provider"]
        print(f"\n  ┌─ {p.full_name} ({'Female' if p.gender=='F' else 'Male'})")
        print(f"  │  NPI       : {p.npi}")
        print(f"  │  Specialty : {p.specialty}")
        print(f"  │  Hospital  : {p.hospital}  ({p.region})")
        print(f"  │  Experience: {p.years_exp} years")
        print(f"  │")
        print(f"  │  Out-degree : {detail['out_degree']}  "
              f"({detail['total_sent']:,} referrals sent)")
        print(f"  │  In-degree  : {detail['in_degree']}  "
              f"({detail['total_received']:,} referrals received)")
        print(f"  └─")

        if detail["top_referrals_sent"]:
            print("\n  Top providers referred TO:")
            for prov, cnt in detail["top_referrals_sent"][:5]:
                print(f"    → {prov.full_name} ({prov.specialty})  ×{cnt}")
        if detail["top_referrals_received"]:
            print("\n  Top providers referring FROM:")
            for prov, cnt in detail["top_referrals_received"][:5]:
                print(f"    ← {prov.full_name} ({prov.specialty})  ×{cnt}")
    _pause()


def mode_centrality(net: ReferralNetwork) -> None:
    """INTERACTION MODE 3 – Top-central providers."""
    _sep("MODE 3 – Top Central Providers")
    print("  Metrics: degree | betweenness | in_degree | out_degree")
    metric    = _prompt("Metric", "degree")
    specialty = _prompt("Specialty filter (or blank for all)", "")
    n_str     = _prompt("How many results", "10")
    try:
        n = int(n_str)
    except ValueError:
        n = 10

    results = net.top_central(metric=metric, n=n, specialty=specialty)
    label = f"Top {len(results)} by {metric} centrality"
    if specialty:
        label += f" ({specialty})"
    print(f"\n  {label}:\n")
    for rank, (prov, score) in enumerate(results, 1):
        bar = "█" * int(score * 40)
        print(f"  {rank:>2}. {prov.full_name:<30} {prov.specialty:<22} "
              f"score={score:.4f}  {bar}")
    _pause()


def mode_path(net: ReferralNetwork) -> None:
    """INTERACTION MODE 4 – Find referral path."""
    _sep("MODE 4 – Find Referral Path")
    from_npi = _prompt("From NPI")
    to_npi   = _prompt("To NPI  ")

    src = net.get_provider(from_npi)
    dst = net.get_provider(to_npi)
    if src is None:
        print(f"\n  NPI {from_npi!r} not found.")
        _pause()
        return
    if dst is None:
        print(f"\n  NPI {to_npi!r} not found.")
        _pause()
        return

    result = net.find_referral_path(from_npi, to_npi)
    if result is None:
        print(f"\n  No referral path found between "
              f"{src.full_name} and {dst.full_name}.")
    else:
        print(f"\n  Referral path: {src.full_name} → {dst.full_name}")
        print(f"  Hops: {result['hops']}  |  "
              f"Total referrals along path: {result['total_weight']:,}\n")
        for i, prov in enumerate(result["path"]):
            connector = "  START → " if i == 0 else "        → "
            print(f"  {connector}{prov.full_name} ({prov.specialty})")
        print()
        print("  Edge details:")
        for a, b, w in result["edges"]:
            print(f"    {a.full_name:<30} →  {b.full_name:<30}  ×{w}")
    _pause()


def mode_filter_specialty(net: ReferralNetwork) -> None:
    """INTERACTION MODE 5 – Filter referrals by specialty pair."""
    _sep("MODE 5 – Filter by Specialty")
    from_spec = _prompt("From specialty (partial)")
    to_spec   = _prompt("To specialty (partial, or blank for all)", "")

    rows = net.filter_by_specialty(from_spec, to_spec)
    if not rows:
        print("\n  No referral edges matched.")
    else:
        print(f"\n  {len(rows)} referral edge(s) found "
              f"(showing top 20 by volume):\n")
        header = f"  {'From':<30}  {'To':<30}  {'Count':>6}"
        print(header)
        print("  " + "─" * 70)
        for src, dst, cnt in rows[:20]:
            print(f"  {src.full_name:<30}  {dst.full_name:<30}  {cnt:>6,}")
    _pause()


def mode_summary(net: ReferralNetwork) -> None:
    """INTERACTION MODE 6 – Network summary statistics."""
    _sep("MODE 6 – Network Summary")
    s = net.referral_summary()
    print(f"\n  Providers  : {s['total_providers']}")
    print(f"  Edges      : {s['total_edges']:,}")
    print(f"  Referrals  : {s['total_referrals']:,}")
    print(f"  Density    : {s['density']:.4f}")
    print(f"  Avg out-deg: {s['avg_out_degree']}")

    print("\n  Providers by specialty:")
    for spec, cnt in sorted(s["providers_per_specialty"].items()):
        print(f"    {spec:<25} {cnt}")

    print("\n  Providers by region:")
    for reg, cnt in sorted(s["providers_per_region"].items()):
        print(f"    {reg:<25} {cnt}")

    print("\n  Top 10 specialty referral corridors:")
    print(f"  {'From':<25}  {'To':<25}  {'Referrals':>10}")
    print("  " + "─" * 65)
    for frm, to, cnt in s["top_specialty_pairs"]:
        print(f"  {frm:<25}  {to:<25}  {cnt:>10,}")
    _pause()


# ── main menu ─────────────────────────────────────────────────────────────────

MENU = """
  ┌────────────────────────────────────────────────────┐
  │   Healthcare Provider Referral Network – SI 507    │
  ├────────────────────────────────────────────────────┤
  │  1. Search providers                               │
  │  2. View provider detail                           │
  │  3. Top-central providers                          │
  │  4. Find referral path between two providers       │
  │  5. Filter referrals by specialty                  │
  │  6. Network summary & statistics                   │
  │  q. Quit                                           │
  └────────────────────────────────────────────────────┘
"""

HANDLERS = {
    "1": mode_search,
    "2": mode_detail,
    "3": mode_centrality,
    "4": mode_path,
    "5": mode_filter_specialty,
    "6": mode_summary,
}


def main() -> None:
    print("\nLoading referral network …", end=" ", flush=True)
    net = ReferralNetwork()
    print(f"done.  ({net.node_count()} providers, {net.edge_count():,} edges)\n")

    while True:
        print(MENU)
        choice = input("  Select an option: ").strip().lower()
        if choice in ("q", "quit", "exit"):
            print("\n  Goodbye!\n")
            break
        handler = HANDLERS.get(choice)
        if handler is None:
            print("  Invalid choice.  Please enter 1–6 or q.")
        else:
            handler(net)


if __name__ == "__main__":
    main()
