"""
app.py
──────
Streamlit web application for the Healthcare Provider Referral Network.

Run with:
    streamlit run app.py

Requires:
    pip install streamlit plotly networkx pandas

All six interaction modes are available through the sidebar navigation.

Author : Woody Wu  (wuwoody)
Course : SI 507 – Final Project
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import streamlit as st

# ── optional plotly import (graceful fallback) ───────────────────────────────
try:
    import plotly.graph_objects as go
    import plotly.express as px
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

from models import ReferralNetwork

# ── page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Healthcare Referral Network",
    page_icon="🏥",
    layout="wide",
)

# ── cached network load ───────────────────────────────────────────────────────

@st.cache_resource
def load_network() -> ReferralNetwork:
    data_dir = Path("data")
    if not (data_dir / "providers.csv").exists():
        import subprocess, sys
        subprocess.run([sys.executable, "generate_data.py"], check=True)
    return ReferralNetwork()


NET = load_network()

# ── sidebar ───────────────────────────────────────────────────────────────────

st.sidebar.title("🏥 Referral Network")
st.sidebar.markdown(f"**{NET.node_count()} providers** · **{NET.edge_count():,} edges**")
st.sidebar.markdown("---")

MODE = st.sidebar.radio(
    "Navigate",
    [
        "1 · Search Providers",
        "2 · Provider Detail",
        "3 · Top Central",
        "4 · Referral Path",
        "5 · Specialty Filter",
        "6 · Network Summary",
    ],
)

# ─────────────────────────────────────────────────────────────────────────────
# MODE 1 – Search Providers
# ─────────────────────────────────────────────────────────────────────────────

if MODE.startswith("1"):
    st.header("🔍 Search Providers")

    col1, col2, col3 = st.columns(3)
    query     = col1.text_input("Name (partial)")
    specialty = col2.selectbox(
        "Specialty",
        [""] + sorted({p.specialty for p in NET.providers.values()}),
    )
    region    = col3.selectbox(
        "Region",
        [""] + sorted({p.region for p in NET.providers.values()}),
    )

    results = NET.search_provider(query, specialty, region)
    st.markdown(f"**{len(results)} providers found**")

    if results:
        df = pd.DataFrame([{
            "NPI":        p.npi,
            "Name":       p.full_name,
            "Specialty":  p.specialty,
            "Region":     p.region,
            "Hospital":   p.hospital,
            "Experience": f"{p.years_exp} yrs",
        } for p in results])
        st.dataframe(df, use_container_width=True)

        if HAS_PLOTLY:
            spec_counts = df["Specialty"].value_counts().reset_index()
            spec_counts.columns = ["Specialty", "Count"]
            fig = px.bar(spec_counts, x="Specialty", y="Count",
                         title="Results by Specialty", color="Specialty")
            st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# MODE 2 – Provider Detail
# ─────────────────────────────────────────────────────────────────────────────

elif MODE.startswith("2"):
    st.header("👤 Provider Detail")

    all_npis = sorted(NET.providers.keys())
    options  = [f"{npi} – {NET.providers[npi].full_name}" for npi in all_npis]
    choice   = st.selectbox("Select a provider", options)
    npi      = choice.split(" – ")[0]

    detail = NET.get_provider_detail(npi)
    if detail:
        p = detail["provider"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Referrals Sent",     f"{detail['total_sent']:,}")
        c2.metric("Referrals Received", f"{detail['total_received']:,}")
        c3.metric("Refers TO",          detail["out_degree"])
        c4.metric("Referred BY",        detail["in_degree"])

        st.markdown(f"""
**{p.full_name}**  
`{p.npi}` · {p.specialty} · {p.hospital} · {p.region}  
Experience: {p.years_exp} years
""")

        col_l, col_r = st.columns(2)
        with col_l:
            st.subheader("Top Referrals Sent")
            if detail["top_referrals_sent"]:
                df_sent = pd.DataFrame([{
                    "Provider": f"{pr.full_name} ({pr.specialty})",
                    "Count":    cnt,
                } for pr, cnt in detail["top_referrals_sent"]])
                st.dataframe(df_sent, use_container_width=True)

        with col_r:
            st.subheader("Top Referrals Received")
            if detail["top_referrals_received"]:
                df_recv = pd.DataFrame([{
                    "Provider": f"{pr.full_name} ({pr.specialty})",
                    "Count":    cnt,
                } for pr, cnt in detail["top_referrals_received"]])
                st.dataframe(df_recv, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# MODE 3 – Top Central
# ─────────────────────────────────────────────────────────────────────────────

elif MODE.startswith("3"):
    st.header("📊 Top Central Providers")

    col1, col2, col3 = st.columns(3)
    metric    = col1.selectbox("Metric", ["degree", "betweenness", "in_degree", "out_degree"])
    n         = col2.slider("Top N", 5, 30, 15)
    specialty = col3.selectbox(
        "Specialty filter",
        [""] + sorted({p.specialty for p in NET.providers.values()}),
    )

    results = NET.top_central(metric=metric, n=n, specialty=specialty)
    if results:
        df = pd.DataFrame([{
            "Rank":      i + 1,
            "Provider":  prov.full_name,
            "Specialty": prov.specialty,
            "Region":    prov.region,
            "Score":     round(score, 5),
        } for i, (prov, score) in enumerate(results)])

        if HAS_PLOTLY:
            fig = px.bar(
                df, x="Score", y="Provider", orientation="h",
                color="Specialty",
                title=f"Top {n} providers by {metric} centrality",
            )
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.dataframe(df, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# MODE 4 – Referral Path
# ─────────────────────────────────────────────────────────────────────────────

elif MODE.startswith("4"):
    st.header("🔗 Find Referral Path")

    all_npis = sorted(NET.providers.keys())
    opts     = [f"{npi} – {NET.providers[npi].full_name}" for npi in all_npis]

    col1, col2 = st.columns(2)
    src_choice = col1.selectbox("From provider", opts, key="src")
    dst_choice = col2.selectbox("To provider",   opts, key="dst", index=min(5, len(opts)-1))

    src_npi = src_choice.split(" – ")[0]
    dst_npi = dst_choice.split(" – ")[0]

    if st.button("Find Path", type="primary"):
        result = NET.find_referral_path(src_npi, dst_npi)
        if result is None:
            st.error("No referral path found between these two providers.")
        else:
            st.success(
                f"Path found!  **{result['hops']} intermediate hops** · "
                f"**{result['total_weight']:,} total referrals** along path"
            )
            # Path display
            path_html = " → ".join(
                f"<b>{p.full_name}</b><br><small>{p.specialty}</small>"
                for p in result["path"]
            )
            st.markdown(f"<div style='font-size:1.1em'>{path_html}</div>",
                        unsafe_allow_html=True)

            # Edge table
            st.subheader("Edge breakdown")
            df_edges = pd.DataFrame([{
                "From":   f"{a.full_name} ({a.specialty})",
                "To":     f"{b.full_name} ({b.specialty})",
                "Count":  w,
            } for a, b, w in result["edges"]])
            st.dataframe(df_edges, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# MODE 5 – Specialty Filter
# ─────────────────────────────────────────────────────────────────────────────

elif MODE.startswith("5"):
    st.header("🏷️ Filter Referrals by Specialty")

    specs = sorted({p.specialty for p in NET.providers.values()})
    col1, col2 = st.columns(2)
    from_spec = col1.selectbox("From specialty", specs)
    to_spec   = col2.selectbox("To specialty (blank = all)", [""] + specs)

    rows = NET.filter_by_specialty(from_spec, to_spec)
    st.markdown(f"**{len(rows)} referral edges found**")
    if rows:
        df = pd.DataFrame([{
            "From":     f"{s.full_name}",
            "From Spec":  s.specialty,
            "To":       f"{d.full_name}",
            "To Spec":    d.specialty,
            "Referrals":  cnt,
        } for s, d, cnt in rows[:100]])
        st.dataframe(df, use_container_width=True)

        if HAS_PLOTLY:
            top20 = df.head(20)
            fig = px.bar(top20, x="Referrals", y="From", orientation="h",
                         color="To Spec",
                         title=f"Top 20 referral edges: {from_spec} → {to_spec or 'all'}")
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# MODE 6 – Network Summary
# ─────────────────────────────────────────────────────────────────────────────

elif MODE.startswith("6"):
    st.header("📈 Network Summary & Statistics")

    s = NET.referral_summary()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Providers",   s["total_providers"])
    c2.metric("Edges",       f"{s['total_edges']:,}")
    c3.metric("Referrals",   f"{s['total_referrals']:,}")
    c4.metric("Density",     f"{s['density']:.4f}")
    c5.metric("Avg Out-Deg", s["avg_out_degree"])

    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("Providers by Specialty")
        df_spec = pd.DataFrame(
            list(s["providers_per_specialty"].items()),
            columns=["Specialty", "Count"],
        ).sort_values("Count", ascending=False)
        if HAS_PLOTLY:
            fig = px.pie(df_spec, names="Specialty", values="Count")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.dataframe(df_spec, use_container_width=True)

    with col_r:
        st.subheader("Providers by Region")
        df_reg = pd.DataFrame(
            list(s["providers_per_region"].items()),
            columns=["Region", "Count"],
        ).sort_values("Count", ascending=False)
        if HAS_PLOTLY:
            fig = px.bar(df_reg, x="Region", y="Count", color="Region")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.dataframe(df_reg, use_container_width=True)

    st.subheader("Top Specialty Referral Corridors")
    df_pairs = pd.DataFrame(
        s["top_specialty_pairs"],
        columns=["From Specialty", "To Specialty", "Total Referrals"],
    )
    if HAS_PLOTLY:
        fig = px.bar(df_pairs, x="Total Referrals",
                     y=df_pairs["From Specialty"] + " → " + df_pairs["To Specialty"],
                     orientation="h", title="Top 10 Referral Corridors by Volume")
        fig.update_layout(yaxis=dict(autorange="reversed"),
                          yaxis_title="Specialty Pair")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.dataframe(df_pairs, use_container_width=True)
