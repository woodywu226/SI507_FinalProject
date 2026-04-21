"""
models.py
─────────
Object-oriented core for the Healthcare Provider Referral Network.

Classes
───────
Provider           – Represents a single physician / healthcare provider.
ReferralNetwork    – Directed, weighted NetworkX graph of provider referrals
                     plus all analytical and interaction methods.

Author : Woody Wu  (wuwoody)
Course : SI 507 – Final Project
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import networkx as nx


# ── Provider ─────────────────────────────────────────────────────────────────

@dataclass
class Provider:
    """
    A single healthcare provider (physician or specialist).

    Attributes
    ----------
    npi        : str   – National Provider Identifier (10-digit unique ID).
    first_name : str
    last_name  : str
    specialty  : str   – Medical specialty (e.g. 'Cardiology').
    region     : str   – Geographic region.
    hospital   : str   – Primary affiliated hospital or clinic.
    gender     : str   – 'M' or 'F'.
    years_exp  : int   – Years of clinical experience.
    """

    npi:        str
    first_name: str
    last_name:  str
    specialty:  str
    region:     str
    hospital:   str
    gender:     str  = "U"
    years_exp:  int  = 0

    # ── computed properties ──────────────────────────────────────────────────

    @property
    def full_name(self) -> str:
        """Return 'Dr. <First> <Last>'."""
        return f"Dr. {self.first_name} {self.last_name}"

    @property
    def display_id(self) -> str:
        """Short identifier used in CLI output."""
        return f"[{self.npi}] {self.full_name} ({self.specialty})"

    # ── class methods ────────────────────────────────────────────────────────

    @classmethod
    def from_dict(cls, row: dict) -> "Provider":
        """
        Construct a Provider from a CSV-row dictionary.

        Parameters
        ----------
        row : dict
            Must contain keys: npi, first_name, last_name, specialty,
            region, hospital.  gender and years_exp are optional.
        """
        return cls(
            npi        = row["npi"].strip(),
            first_name = row["first_name"].strip(),
            last_name  = row["last_name"].strip(),
            specialty  = row["specialty"].strip(),
            region     = row["region"].strip(),
            hospital   = row["hospital"].strip(),
            gender     = row.get("gender", "U").strip(),
            years_exp  = int(row.get("years_exp", 0)),
        )

    def __repr__(self) -> str:
        return (
            f"Provider(npi={self.npi!r}, name={self.full_name!r}, "
            f"specialty={self.specialty!r}, region={self.region!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Provider):
            return NotImplemented
        return self.npi == other.npi

    def __hash__(self) -> int:
        return hash(self.npi)


# ── ReferralNetwork ───────────────────────────────────────────────────────────

class ReferralNetwork:
    """
    A directed, weighted graph of healthcare provider referrals.

    The graph is built on top of NetworkX's DiGraph.  Each node is an NPI
    string; full Provider objects are stored as node attributes.  Edge
    weights represent the total referral count between two providers.

    Interaction Modes (≥ 4 required by rubric)
    ─────────────────────────────────────────
    1. search_provider     – find providers by name, specialty, or region
    2. get_provider_detail – full profile + neighbours for one provider
    3. top_central         – rank providers by degree / betweenness centrality
    4. find_referral_path  – shortest weighted path between two providers
    5. filter_by_specialty – subgraph view filtered to a specialty pair
    6. referral_summary    – aggregate statistics for the network

    Parameters
    ----------
    providers_csv : str | Path
        Path to providers.csv (NPI, name, specialty, region, hospital …)
    referrals_csv : str | Path
        Path to referrals.csv (from_npi, to_npi, referral_count, year)
    """

    def __init__(
        self,
        providers_csv: str | Path = "data/providers.csv",
        referrals_csv: str | Path = "data/referrals.csv",
    ) -> None:
        self._graph: nx.DiGraph = nx.DiGraph()
        self._providers: dict[str, Provider] = {}
        self._load_providers(providers_csv)
        self._load_referrals(referrals_csv)

    # ── loading ──────────────────────────────────────────────────────────────

    def _load_providers(self, path: str | Path) -> None:
        """Load provider records and add them as graph nodes."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(
                f"providers.csv not found at {path}.  "
                "Run 'python generate_data.py' first."
            )
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                prov = Provider.from_dict(row)
                self._providers[prov.npi] = prov
                self._graph.add_node(prov.npi, provider=prov)

    def _load_referrals(self, path: str | Path) -> None:
        """Load referral edges and add them to the graph."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(
                f"referrals.csv not found at {path}.  "
                "Run 'python generate_data.py' first."
            )
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                src  = row["from_npi"].strip()
                dst  = row["to_npi"].strip()
                cnt  = int(row["referral_count"])
                if src in self._providers and dst in self._providers:
                    if self._graph.has_edge(src, dst):
                        self._graph[src][dst]["weight"] += cnt
                    else:
                        self._graph.add_edge(src, dst, weight=cnt)

    # ── basic accessors ───────────────────────────────────────────────────────

    @property
    def graph(self) -> nx.DiGraph:
        """Expose the underlying NetworkX DiGraph (read-only use)."""
        return self._graph

    @property
    def providers(self) -> dict[str, Provider]:
        """Return the NPI → Provider mapping."""
        return self._providers

    def get_provider(self, npi: str) -> Optional[Provider]:
        """Return a Provider by NPI, or None if not found."""
        return self._providers.get(npi)

    def node_count(self) -> int:
        """Total number of provider nodes."""
        return self._graph.number_of_nodes()

    def edge_count(self) -> int:
        """Total number of directed referral edges."""
        return self._graph.number_of_edges()

    # ─────────────────────────────────────────────────────────────────────────
    # INTERACTION MODE 1 – search_provider
    # ─────────────────────────────────────────────────────────────────────────

    def search_provider(
        self,
        query: str = "",
        specialty: str = "",
        region: str = "",
    ) -> list[Provider]:
        """
        Search for providers by free-text name, specialty, and/or region.

        Parameters
        ----------
        query     : str  – Partial match against provider full name (case-insensitive).
        specialty : str  – Exact or partial match against specialty field.
        region    : str  – Exact or partial match against region field.

        Returns
        -------
        list[Provider] – All providers matching every supplied filter.
                         Returns all providers when all filters are empty.
        """
        q    = query.lower().strip()
        spec = specialty.lower().strip()
        reg  = region.lower().strip()

        results = []
        for prov in self._providers.values():
            if q    and q    not in prov.full_name.lower():
                continue
            if spec and spec not in prov.specialty.lower():
                continue
            if reg  and reg  not in prov.region.lower():
                continue
            results.append(prov)

        return sorted(results, key=lambda p: (p.last_name, p.first_name))

    # ─────────────────────────────────────────────────────────────────────────
    # INTERACTION MODE 2 – get_provider_detail
    # ─────────────────────────────────────────────────────────────────────────

    def get_provider_detail(self, npi: str) -> Optional[dict]:
        """
        Return a full profile dict for a provider including network neighbours.

        The dict contains:
          - 'provider'      : Provider object
          - 'out_degree'    : number of providers this one refers TO
          - 'in_degree'     : number of providers that refer TO this one
          - 'total_sent'    : total referrals sent (sum of out-edge weights)
          - 'total_received': total referrals received (sum of in-edge weights)
          - 'top_referrals_sent'    : list of (Provider, count) sorted descending
          - 'top_referrals_received': list of (Provider, count) sorted descending

        Returns None if the NPI is not in the network.
        """
        if npi not in self._providers:
            return None

        out_edges = list(self._graph.out_edges(npi, data=True))
        in_edges  = list(self._graph.in_edges(npi, data=True))

        sent = sorted(
            [(self._providers[dst], d["weight"]) for _, dst, d in out_edges],
            key=lambda x: x[1], reverse=True,
        )
        received = sorted(
            [(self._providers[src], d["weight"]) for src, _, d in in_edges],
            key=lambda x: x[1], reverse=True,
        )

        return {
            "provider":               self._providers[npi],
            "out_degree":             len(out_edges),
            "in_degree":              len(in_edges),
            "total_sent":             sum(d["weight"] for *_, d in out_edges),
            "total_received":         sum(d["weight"] for *_, d in in_edges),
            "top_referrals_sent":     sent[:10],
            "top_referrals_received": received[:10],
        }

    # ─────────────────────────────────────────────────────────────────────────
    # INTERACTION MODE 3 – top_central
    # ─────────────────────────────────────────────────────────────────────────

    def top_central(
        self,
        metric: str = "degree",
        n: int = 10,
        specialty: str = "",
    ) -> list[tuple[Provider, float]]:
        """
        Rank providers by centrality.

        Parameters
        ----------
        metric    : 'degree' | 'betweenness' | 'in_degree' | 'out_degree'
        n         : number of top results to return
        specialty : optional filter to restrict results to one specialty

        Returns
        -------
        list of (Provider, score) tuples, sorted descending by score.
        """
        g = self._graph

        # optionally restrict to a specialty subgraph
        if specialty:
            nodes = [
                npi for npi, p in self._providers.items()
                if specialty.lower() in p.specialty.lower()
            ]
            g = g.subgraph(nodes)

        if metric == "degree":
            scores = nx.degree_centrality(g)
        elif metric == "betweenness":
            scores = nx.betweenness_centrality(g, weight="weight", normalized=True)
        elif metric == "in_degree":
            scores = nx.in_degree_centrality(g)
        elif metric == "out_degree":
            scores = nx.out_degree_centrality(g)
        else:
            raise ValueError(f"Unknown metric {metric!r}. "
                             "Choose: degree, betweenness, in_degree, out_degree")

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [
            (self._providers[npi], score)
            for npi, score in ranked[:n]
            if npi in self._providers
        ]

    # ─────────────────────────────────────────────────────────────────────────
    # INTERACTION MODE 4 – find_referral_path
    # ─────────────────────────────────────────────────────────────────────────

    def find_referral_path(
        self,
        from_npi: str,
        to_npi:   str,
    ) -> Optional[dict]:
        """
        Find the shortest referral path between two providers.

        Uses Dijkstra with inverse-weight (more referrals = shorter
        effective distance) so the returned path follows the most-used
        referral corridors.

        Returns
        -------
        dict with keys:
          - 'path'        : list[Provider] from source to target
          - 'hops'        : number of intermediate providers
          - 'total_weight': sum of referral counts along path
          - 'edges'       : list of (Provider, Provider, weight)
        Or None if no path exists.
        """
        if from_npi not in self._providers or to_npi not in self._providers:
            return None

        # Build a version of the graph where weight = 1/(referral_count)
        # so Dijkstra finds the most-trafficked corridor.
        inv_graph = nx.DiGraph()
        for u, v, d in self._graph.edges(data=True):
            inv_graph.add_edge(u, v, weight=1.0 / max(d["weight"], 1))

        try:
            npi_path = nx.dijkstra_path(inv_graph, from_npi, to_npi, weight="weight")
        except nx.NetworkXNoPath:
            return None

        prov_path = [self._providers[n] for n in npi_path]
        edges = []
        total = 0
        for a, b in zip(npi_path, npi_path[1:]):
            w = self._graph[a][b]["weight"]
            total += w
            edges.append((self._providers[a], self._providers[b], w))

        return {
            "path":         prov_path,
            "hops":         len(npi_path) - 2,
            "total_weight": total,
            "edges":        edges,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # INTERACTION MODE 5 – filter_by_specialty
    # ─────────────────────────────────────────────────────────────────────────

    def filter_by_specialty(
        self,
        from_specialty: str,
        to_specialty:   str = "",
    ) -> list[tuple[Provider, Provider, int]]:
        """
        Return all referral edges from one specialty to another (or all targets).

        Parameters
        ----------
        from_specialty : source specialty (partial, case-insensitive)
        to_specialty   : target specialty filter (partial); '' = all targets

        Returns
        -------
        list of (from_Provider, to_Provider, referral_count) tuples,
        sorted by referral_count descending.
        """
        results = []
        for u, v, d in self._graph.edges(data=True):
            src = self._providers.get(u)
            dst = self._providers.get(v)
            if src is None or dst is None:
                continue
            if from_specialty.lower() not in src.specialty.lower():
                continue
            if to_specialty and to_specialty.lower() not in dst.specialty.lower():
                continue
            results.append((src, dst, d["weight"]))
        return sorted(results, key=lambda x: x[2], reverse=True)

    # ─────────────────────────────────────────────────────────────────────────
    # INTERACTION MODE 6 – referral_summary
    # ─────────────────────────────────────────────────────────────────────────

    def referral_summary(self) -> dict:
        """
        Return aggregate statistics about the referral network.

        Keys in returned dict
        ─────────────────────
        total_providers      : int
        total_edges          : int
        total_referrals      : int   (sum of all edge weights)
        density              : float (0–1)
        avg_out_degree       : float
        top_specialty_pairs  : list[(from_spec, to_spec, count)] top 10
        providers_per_specialty : dict[specialty -> count]
        providers_per_region    : dict[region -> count]
        """
        g = self._graph

        # specialty-pair volumes
        pair_counts: dict[tuple[str, str], int] = {}
        for u, v, d in g.edges(data=True):
            src_spec = self._providers[u].specialty
            dst_spec = self._providers[v].specialty
            key = (src_spec, dst_spec)
            pair_counts[key] = pair_counts.get(key, 0) + d["weight"]

        top_pairs = sorted(pair_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        spec_counts: dict[str, int] = {}
        reg_counts:  dict[str, int] = {}
        for p in self._providers.values():
            spec_counts[p.specialty] = spec_counts.get(p.specialty, 0) + 1
            reg_counts[p.region]     = reg_counts.get(p.region,     0) + 1

        out_degrees = [d for _, d in g.out_degree()]
        avg_out = sum(out_degrees) / len(out_degrees) if out_degrees else 0

        return {
            "total_providers":          g.number_of_nodes(),
            "total_edges":              g.number_of_edges(),
            "total_referrals":          sum(d["weight"] for *_, d in g.edges(data=True)),
            "density":                  nx.density(g),
            "avg_out_degree":           round(avg_out, 2),
            "top_specialty_pairs":      [
                (k[0], k[1], v) for k, v in top_pairs
            ],
            "providers_per_specialty":  spec_counts,
            "providers_per_region":     reg_counts,
        }
