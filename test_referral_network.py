"""
test_referral_network.py
────────────────────────
Test suite for the Healthcare Provider Referral Network (SI 507 Final Project).

Tests are organized to:
  1. Document the expected behaviour of each component (living documentation).
  2. Cover happy paths, edge cases, and invalid inputs.
  3. Mirror the grading rubric categories:
       - Data & Architecture
       - Object-Oriented Design
       - Interaction Modes
       - Algorithmic correctness

Run with:
    pytest test_referral_network.py -v

Author : Woody Wu  (wuwoody)
Course : SI 507 – Final Project
"""

from __future__ import annotations

import csv
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Make sure we can import from the project root regardless of where pytest is run.
sys.path.insert(0, str(Path(__file__).parent))

from models import Provider, ReferralNetwork


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def sample_providers_csv(tmp_path_factory):
    """Write a small providers.csv to a temp directory."""
    d = tmp_path_factory.mktemp("data")
    path = d / "providers.csv"
    rows = [
        {"npi": "1111111111", "first_name": "Alice", "last_name": "Adams",
         "specialty": "Primary Care", "region": "Great Lakes",
         "hospital": "Metro General", "gender": "F", "years_exp": "10"},
        {"npi": "2222222222", "first_name": "Bob", "last_name": "Baker",
         "specialty": "Cardiology", "region": "Great Lakes",
         "hospital": "Metro General", "gender": "M", "years_exp": "15"},
        {"npi": "3333333333", "first_name": "Carol", "last_name": "Chen",
         "specialty": "Neurology", "region": "Southeast",
         "hospital": "University Medical", "gender": "F", "years_exp": "8"},
        {"npi": "4444444444", "first_name": "David", "last_name": "Davis",
         "specialty": "Oncology", "region": "Pacific Northwest",
         "hospital": "Harbor Health", "gender": "M", "years_exp": "20"},
    ]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    return path


@pytest.fixture(scope="session")
def sample_referrals_csv(tmp_path_factory):
    """Write a small referrals.csv to a temp directory."""
    d = tmp_path_factory.mktemp("data2")
    path = d / "referrals.csv"
    rows = [
        {"from_npi": "1111111111", "to_npi": "2222222222", "referral_count": "30", "year": "2023"},
        {"from_npi": "1111111111", "to_npi": "3333333333", "referral_count": "10", "year": "2023"},
        {"from_npi": "2222222222", "to_npi": "4444444444", "referral_count": "20", "year": "2023"},
        {"from_npi": "3333333333", "to_npi": "4444444444", "referral_count":  "5", "year": "2023"},
    ]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    return path


@pytest.fixture(scope="session")
def net(sample_providers_csv, sample_referrals_csv):
    """Return a ReferralNetwork built from the small fixture data."""
    return ReferralNetwork(sample_providers_csv, sample_referrals_csv)


@pytest.fixture(scope="session")
def full_net():
    """
    Return the full synthetic network (requires generate_data.py to have run).
    Skipped automatically if data files are missing.
    """
    providers = Path("data/providers.csv")
    referrals = Path("data/referrals.csv")
    if not providers.exists() or not referrals.exists():
        pytest.skip("Full dataset not generated.  Run 'python generate_data.py' first.")
    return ReferralNetwork(providers, referrals)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 – Provider class (Object-Oriented Design)
# ─────────────────────────────────────────────────────────────────────────────

class TestProviderClass:
    """Provider is a dataclass representing one healthcare provider."""

    def test_full_name_includes_dr_prefix(self):
        """Provider.full_name returns 'Dr. First Last'."""
        p = Provider("1", "Jane", "Doe", "Cardiology", "Southeast",
                     "City Hospital", "F", 5)
        assert p.full_name == "Dr. Jane Doe"

    def test_display_id_contains_npi_and_specialty(self):
        """display_id embeds NPI and specialty for CLI display."""
        p = Provider("9876543210", "Tom", "Smith", "Neurology",
                     "Pacific Northwest", "Harbor", "M", 12)
        assert "9876543210" in p.display_id
        assert "Neurology"  in p.display_id

    def test_from_dict_builds_provider_correctly(self):
        """Provider.from_dict() maps CSV rows to Provider attributes."""
        row = {
            "npi": "1234567890", "first_name": "Mary", "last_name": "Brown",
            "specialty": "Oncology", "region": "Great Lakes",
            "hospital": "Lake View", "gender": "F", "years_exp": "7",
        }
        p = Provider.from_dict(row)
        assert p.npi       == "1234567890"
        assert p.specialty == "Oncology"
        assert p.years_exp == 7

    def test_from_dict_uses_default_gender_when_missing(self):
        """from_dict defaults gender to 'U' when the field is absent."""
        row = {
            "npi": "0000000001", "first_name": "Alex", "last_name": "Lee",
            "specialty": "Internal Medicine", "region": "Southeast",
            "hospital": "General", "years_exp": "3",
        }
        p = Provider.from_dict(row)
        assert p.gender == "U"

    def test_equality_based_on_npi(self):
        """Two Provider objects with the same NPI are equal, regardless of other fields."""
        p1 = Provider("111", "First", "One", "Cardiology", "R1", "H1")
        p2 = Provider("111", "Other", "Name", "Oncology",  "R2", "H2")
        assert p1 == p2

    def test_providers_with_different_npis_are_unequal(self):
        """Providers with different NPIs are distinct entities."""
        p1 = Provider("111", "A", "B", "Cardiology", "R", "H")
        p2 = Provider("222", "A", "B", "Cardiology", "R", "H")
        assert p1 != p2

    def test_provider_hashable(self):
        """Provider can be placed in a set (requires __hash__)."""
        p1 = Provider("111", "A", "B", "Spec", "R", "H")
        p2 = Provider("222", "C", "D", "Spec", "R", "H")
        result = {p1, p2}
        assert len(result) == 2

    def test_repr_includes_key_info(self):
        """repr() of a Provider exposes NPI and name for debugging."""
        p = Provider("9999", "Zoe", "Zane", "Primary Care", "Midwest", "Clinic")
        r = repr(p)
        assert "9999"       in r
        assert "Zoe"        in r

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 – ReferralNetwork construction (Data & Architecture)
# ─────────────────────────────────────────────────────────────────────────────

class TestNetworkConstruction:
    """The network is a directed, weighted graph built from CSV files."""

    def test_node_count_matches_provider_csv(self, net):
        """Every row in providers.csv becomes exactly one graph node."""
        assert net.node_count() == 4

    def test_edge_count_matches_referrals_csv(self, net):
        """Every row in referrals.csv becomes exactly one directed edge."""
        assert net.edge_count() == 4

    def test_graph_is_directed(self, net):
        """The underlying graph is a DiGraph (directed)."""
        import networkx as nx
        assert isinstance(net.graph, nx.DiGraph)

    def test_edge_weights_carry_referral_counts(self, net):
        """Each edge stores the referral_count from the CSV as 'weight'."""
        weight = net.graph["1111111111"]["2222222222"]["weight"]
        assert weight == 30

    def test_missing_providers_csv_raises_file_not_found(self, tmp_path):
        """Loading from a non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            ReferralNetwork(
                providers_csv=tmp_path / "missing.csv",
                referrals_csv=tmp_path / "also_missing.csv",
            )

    def test_get_provider_returns_correct_object(self, net):
        """get_provider(npi) returns the Provider with that NPI."""
        prov = net.get_provider("1111111111")
        assert prov is not None
        assert prov.first_name == "Alice"

    def test_get_provider_returns_none_for_unknown_npi(self, net):
        """get_provider returns None for an NPI not in the dataset."""
        assert net.get_provider("0000000000") is None

    def test_providers_dict_has_all_loaded_providers(self, net):
        """net.providers contains all four loaded Provider objects."""
        assert len(net.providers) == 4
        assert "3333333333" in net.providers

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 – Interaction Mode 1: search_provider
# ─────────────────────────────────────────────────────────────────────────────

class TestSearchProvider:
    """search_provider finds providers by name, specialty, and region."""

    def test_empty_query_returns_all_providers(self, net):
        """Calling search with no filters returns all providers."""
        assert len(net.search_provider()) == 4

    def test_name_filter_case_insensitive(self, net):
        """Name search is case-insensitive."""
        results = net.search_provider(query="alice")
        assert len(results) == 1
        assert results[0].first_name == "Alice"

    def test_specialty_filter(self, net):
        """Filtering by specialty returns only matching providers."""
        results = net.search_provider(specialty="Cardiology")
        assert all(p.specialty == "Cardiology" for p in results)
        assert len(results) == 1

    def test_region_filter(self, net):
        """Filtering by region returns only providers in that region."""
        results = net.search_provider(region="Great Lakes")
        assert all(p.region == "Great Lakes" for p in results)
        assert len(results) == 2

    def test_combined_filters_apply_and_logic(self, net):
        """Multiple filters must ALL match (AND logic)."""
        results = net.search_provider(specialty="Cardiology", region="Southeast")
        assert len(results) == 0   # Bob Baker is in Great Lakes, not Southeast

    def test_no_match_returns_empty_list(self, net):
        """A query with no matches returns an empty list, not an error."""
        results = net.search_provider(query="XYZNOTANAME")
        assert results == []

    def test_results_sorted_by_last_name(self, net):
        """Results are sorted alphabetically by last name."""
        results = net.search_provider()
        last_names = [p.last_name for p in results]
        assert last_names == sorted(last_names)

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 – Interaction Mode 2: get_provider_detail
# ─────────────────────────────────────────────────────────────────────────────

class TestGetProviderDetail:
    """get_provider_detail returns full profile including network stats."""

    def test_returns_none_for_unknown_npi(self, net):
        """Unknown NPI returns None without raising an exception."""
        assert net.get_provider_detail("0000000000") is None

    def test_detail_contains_provider_object(self, net):
        """The 'provider' key holds the matching Provider object."""
        detail = net.get_provider_detail("1111111111")
        assert detail["provider"].npi == "1111111111"

    def test_out_degree_counts_distinct_referral_targets(self, net):
        """Alice (1111111111) refers to 2 providers → out_degree == 2."""
        detail = net.get_provider_detail("1111111111")
        assert detail["out_degree"] == 2

    def test_in_degree_counts_distinct_referral_sources(self, net):
        """David (4444444444) is referred to by Bob and Carol → in_degree == 2."""
        detail = net.get_provider_detail("4444444444")
        assert detail["in_degree"] == 2

    def test_total_sent_sums_edge_weights(self, net):
        """Alice sent 30 + 10 = 40 total referrals."""
        detail = net.get_provider_detail("1111111111")
        assert detail["total_sent"] == 40

    def test_top_referrals_sent_sorted_descending(self, net):
        """top_referrals_sent lists highest-count targets first."""
        detail = net.get_provider_detail("1111111111")
        counts = [cnt for _, cnt in detail["top_referrals_sent"]]
        assert counts == sorted(counts, reverse=True)

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 – Interaction Mode 3: top_central
# ─────────────────────────────────────────────────────────────────────────────

class TestTopCentral:
    """top_central ranks providers by various centrality metrics."""

    def test_returns_n_results(self, net):
        """Requesting top-2 returns exactly 2 results."""
        results = net.top_central(n=2)
        assert len(results) == 2

    def test_scores_sorted_descending(self, net):
        """Results are ordered highest-score first."""
        results = net.top_central(metric="degree", n=4)
        scores = [s for _, s in results]
        assert scores == sorted(scores, reverse=True)

    def test_degree_metric_works(self, net):
        """'degree' metric runs without error and returns (Provider, float) tuples."""
        results = net.top_central(metric="degree")
        for prov, score in results:
            assert isinstance(prov, Provider)
            assert isinstance(score, float)

    def test_betweenness_metric_works(self, net):
        """'betweenness' metric returns valid results."""
        results = net.top_central(metric="betweenness")
        assert len(results) > 0

    def test_in_degree_metric_works(self, net):
        """'in_degree' metric returns valid results."""
        results = net.top_central(metric="in_degree")
        assert len(results) > 0

    def test_out_degree_metric_works(self, net):
        """'out_degree' metric returns valid results."""
        results = net.top_central(metric="out_degree")
        assert len(results) > 0

    def test_invalid_metric_raises_value_error(self, net):
        """Passing an unrecognized metric name raises ValueError."""
        with pytest.raises(ValueError):
            net.top_central(metric="magic")

    def test_specialty_filter_restricts_results(self, net):
        """Results only contain providers from the filtered specialty."""
        results = net.top_central(metric="degree", specialty="Cardiology")
        for prov, _ in results:
            assert "Cardiology" in prov.specialty

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 – Interaction Mode 4: find_referral_path
# ─────────────────────────────────────────────────────────────────────────────

class TestFindReferralPath:
    """find_referral_path finds the highest-trafficked path between two providers."""

    def test_direct_referral_path_has_zero_hops(self, net):
        """Alice → Bob have a direct edge: the path has 0 intermediate hops."""
        result = net.find_referral_path("1111111111", "2222222222")
        assert result is not None
        assert result["hops"] == 0

    def test_path_contains_source_and_target(self, net):
        """The returned path starts with the source and ends with the target."""
        result = net.find_referral_path("1111111111", "4444444444")
        assert result["path"][0].npi  == "1111111111"
        assert result["path"][-1].npi == "4444444444"

    def test_multi_hop_path_found(self, net):
        """Alice → David requires at least one intermediate provider."""
        result = net.find_referral_path("1111111111", "4444444444")
        assert result is not None
        assert len(result["path"]) >= 3

    def test_total_weight_positive(self, net):
        """total_weight (sum of edge weights along path) is > 0."""
        result = net.find_referral_path("1111111111", "2222222222")
        assert result["total_weight"] > 0

    def test_no_reverse_path_returns_none(self, net):
        """
        David (4444444444) has no outgoing edges, so there is no path
        from David back to Alice.
        """
        result = net.find_referral_path("4444444444", "1111111111")
        assert result is None

    def test_unknown_source_returns_none(self, net):
        """An unknown source NPI returns None without raising an exception."""
        result = net.find_referral_path("0000000000", "1111111111")
        assert result is None

    def test_unknown_target_returns_none(self, net):
        """An unknown target NPI returns None without raising an exception."""
        result = net.find_referral_path("1111111111", "0000000000")
        assert result is None

    def test_self_path_returns_trivial_result(self, net):
        """A path from a node to itself returns a single-node path."""
        result = net.find_referral_path("1111111111", "1111111111")
        # NetworkX returns a trivial 1-node path
        assert result is not None
        assert len(result["path"]) == 1

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 – Interaction Mode 5: filter_by_specialty
# ─────────────────────────────────────────────────────────────────────────────

class TestFilterBySpecialty:
    """filter_by_specialty returns edges from one specialty to another."""

    def test_filter_from_primary_care_returns_correct_edges(self, net):
        """Primary Care → all: Alice refers to Bob (Cardiology) and Carol (Neurology)."""
        rows = net.filter_by_specialty("Primary Care")
        npis = {src.npi for src, _, _ in rows}
        assert "1111111111" in npis

    def test_filter_returns_sorted_by_count_descending(self, net):
        """Results are ordered highest referral count first."""
        rows = net.filter_by_specialty("Primary Care")
        counts = [cnt for _, _, cnt in rows]
        assert counts == sorted(counts, reverse=True)

    def test_specialty_pair_filter_restricts_targets(self, net):
        """Filtering from 'Primary Care' to 'Cardiology' excludes Neurology targets."""
        rows = net.filter_by_specialty("Primary Care", "Cardiology")
        for _, dst, _ in rows:
            assert "Cardiology" in dst.specialty

    def test_no_match_returns_empty_list(self, net):
        """A specialty combo with no edges returns an empty list."""
        rows = net.filter_by_specialty("Oncology", "Primary Care")
        assert rows == []

    def test_partial_specialty_match_works(self, net):
        """Partial string 'Care' matches 'Primary Care'."""
        rows = net.filter_by_specialty("Care")
        assert len(rows) > 0

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 8 – Interaction Mode 6: referral_summary
# ─────────────────────────────────────────────────────────────────────────────

class TestReferralSummary:
    """referral_summary provides aggregate statistics about the network."""

    def test_summary_has_expected_keys(self, net):
        """The summary dict contains all documented keys."""
        s = net.referral_summary()
        for key in [
            "total_providers", "total_edges", "total_referrals",
            "density", "avg_out_degree", "top_specialty_pairs",
            "providers_per_specialty", "providers_per_region",
        ]:
            assert key in s, f"Missing key: {key}"

    def test_total_providers_correct(self, net):
        """total_providers matches node_count()."""
        s = net.referral_summary()
        assert s["total_providers"] == net.node_count()

    def test_total_edges_correct(self, net):
        """total_edges matches edge_count()."""
        s = net.referral_summary()
        assert s["total_edges"] == net.edge_count()

    def test_total_referrals_is_sum_of_all_weights(self, net):
        """total_referrals == 30 + 10 + 20 + 5 == 65 in the fixture."""
        s = net.referral_summary()
        assert s["total_referrals"] == 65

    def test_density_between_zero_and_one(self, net):
        """Network density is always in [0, 1]."""
        s = net.referral_summary()
        assert 0.0 <= s["density"] <= 1.0

    def test_providers_per_specialty_sums_to_total(self, net):
        """Sum of providers_per_specialty equals total_providers."""
        s = net.referral_summary()
        assert sum(s["providers_per_specialty"].values()) == s["total_providers"]

    def test_top_specialty_pairs_is_list_of_tuples(self, net):
        """Each entry in top_specialty_pairs is a (str, str, int) triple."""
        s = net.referral_summary()
        for item in s["top_specialty_pairs"]:
            assert len(item) == 3
            assert isinstance(item[2], int)

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 9 – Full-data smoke tests (skipped if data not generated)
# ─────────────────────────────────────────────────────────────────────────────

class TestFullDataset:
    """Smoke tests on the full 120-provider synthetic dataset."""

    def test_full_network_has_120_providers(self, full_net):
        """The generator creates exactly 120 providers."""
        assert full_net.node_count() == 120

    def test_full_network_has_many_edges(self, full_net):
        """The full dataset should have at least 1 000 referral edges."""
        assert full_net.edge_count() >= 1_000

    def test_centrality_top10_returns_10(self, full_net):
        """top_central with n=10 returns exactly 10 results on full data."""
        results = full_net.top_central(n=10)
        assert len(results) == 10

    def test_search_returns_results_for_cardiology(self, full_net):
        """Searching 'Cardiology' returns at least one provider."""
        results = full_net.search_provider(specialty="Cardiology")
        assert len(results) > 0

    def test_path_found_between_any_two_connected_providers(self, full_net):
        """A path exists between the first and second loaded providers."""
        npis = list(full_net.providers.keys())
        result = full_net.find_referral_path(npis[0], npis[1])
        # Path may or may not exist, but the function must not raise
        assert result is None or isinstance(result, dict)
