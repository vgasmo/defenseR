from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import plotly.graph_objects as go
import streamlit as st

# Optional Supabase import – app works even if package is missing
try:
    from supabase import Client, create_client  # type: ignore
except ImportError:  # pragma: no cover
    Client = Any  # type: ignore
    create_client = None  # type: ignore


# -----------------------------------------------------------------------------
# Page config & simple styling
# -----------------------------------------------------------------------------

st.set_page_config(
    page_title="Defence Readiness Radar",
    page_icon="🛡️",
    layout="wide",
)

st.markdown(
    """
<style>
    .main > div {
        padding-top: 1.5rem;
        padding-bottom: 1.5rem;
    }
    .tag {
        display:inline-block;
        padding:2px 8px;
        border-radius:999px;
        font-size:11px;
        font-weight:600;
        margin-left:4px;
    }
    .tag-critical  { background:#fee2e2; color:#b91c1c; }
    .tag-weak      { background:#fef3c7; color:#92400e; }
    .tag-moderate  { background:#e0f2fe; color:#075985; }
    .tag-good      { background:#dcfce7; color:#166534; }
    .tag-strong    { background:#e0e7ff; color:#3730a3; }
</style>
""",
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Supabase client (optional)
# -----------------------------------------------------------------------------


@st.cache_resource
def get_supabase_client() -> Optional["Client"]:
    """
    Create Supabase client if URL and KEY are defined in st.secrets.

    Uses only the public anon key – never the service_role key.
    """
    if create_client is None:
        return None

    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY")

    if not url or not key:
        return None

    return create_client(url, key)


supabase = get_supabase_client()
SUPABASE_ENABLED = supabase is not None

# Company codes stored in Streamlit secrets (shared secrets per tenant)
# Example in .streamlit/secrets.toml or Streamlit Cloud:
#
# [COMPANY_CODES]
# ACME_DEFENCE = "g8F3pZ9kQM4t"
# BETA_TECH    = "Ks72nZ1qXb09"
#
COMPANY_CODES: Dict[str, str] = dict(st.secrets.get("COMPANY_CODES", {}))
AUTH_ENABLED = bool(COMPANY_CODES)

# Persistence (history) only if we have BOTH auth and Supabase
PERSISTENCE_ENABLED = AUTH_ENABLED and SUPABASE_ENABLED

SESSION_TIMEOUT_MINUTES = 60


# -----------------------------------------------------------------------------
# Questionnaire definition
# -----------------------------------------------------------------------------

DIMENSIONS: Dict[str, List[str]] = {
    "Product": [
        "We have at least a functional prototype tested in a relevant environment (pilot, lab, early users).",
        "The product clearly addresses Defence-related needs (surveillance, logistics, cyber, C2, etc.).",
        "We have identified specific Defence technical requirements (standards, interoperability) and started adapting the product.",
        "We have the capacity (in-house or via partners) to deliver pilots or small Defence contracts.",
    ],
    "Market": [
        "We know the main customers and decision-makers in Defence (MoD, Armed Forces, NATO, EU, integrators).",
        "We already had meetings or active contacts with potential Defence clients or partners.",
        "We have strategic partnerships with organisations already established in the Defence sector.",
        "We have a dedicated value proposition for Defence, distinct from our civil/commercial offer.",
    ],
    "Documentation": [
        "Relevant IP (patents, software, trademarks) is identified and protected where needed.",
        "Technical documentation (architectures, specs, manuals, data sheets) is organised and up to date.",
        "We have NDA templates and contract templates suitable for pilots/partnerships in Defence.",
        "We have identified and started relevant licensing/accreditation processes to operate in Defence.",
    ],
    "Security": [
        "We have basic information security policies (access control, passwords, backups, device management).",
        "Sensitive information (code, data, critical docs) is protected (encryption, restricted access, separated environments).",
        "Key staff received awareness/training on cybersecurity and information protection.",
        "Facilities/processes have adequate physical and organisational security (controlled access, visitor logs, restricted areas).",
    ],
    "Certifications": [
        "We have relevant quality certifications (e.g. ISO 9001) OR processes already close to that level.",
        "We have or are implementing information security practices/certifications (e.g. ISO 27001).",
        "We identified Defence-specific or adjacent certifications (aero/space, cyber) that may be required.",
        "There is a certification roadmap with priorities, timelines and estimated resources.",
    ],
}


def interpret_score(score: float) -> str:
    if score <= 1.5:
        return "Critical"
    if score <= 2.5:
        return "Weak"
    if score <= 3.5:
        return "Moderate"
    if score <= 4.5:
        return "Good"
    return "Very strong"


def score_tag_class(score: float) -> str:
    if score <= 1.5:
        return "tag-critical"
    if score <= 2.5:
        return "tag-weak"
    if score <= 3.5:
        return "tag-moderate"
    if score <= 4.5:
        return "tag-good"
    return "tag-strong"


# -----------------------------------------------------------------------------
# Session state & authentication
# -----------------------------------------------------------------------------

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "company_id" not in st.session_state:
    st.session_state.company_id = None
if "last_activity" not in st.session_state:
    st.session_state.last_activity = datetime.utcnow()

# Session timeout (only meaningful when auth is enabled)
if st.session_state.logged_in and AUTH_ENABLED:
    now = datetime.utcnow()
    delta = now - st.session_state.last_activity
    if delta > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
        st.session_state.logged_in = False
        st.session_state.company_id = None
    st.session_state.last_activity = now


with st.sidebar:
    st.title("Company access")

    if not AUTH_ENABLED:
        # Demo mode – no per-company storage, even if Supabase is configured
        st.info(
            "Demo mode: no company-specific login and no data is stored.\n\n"
            "To enable secure per-company history, define COMPANY_CODES in "
            "Streamlit secrets and redeploy."
        )
        st.session_state.logged_in = True
        st.session_state.company_id = "DEMO"
    else:
        st.caption("Sign in with your company ID and access code.")
        company_input = st.text_input("Company ID")
        access_code = st.text_input("Access code", type="password")

        col_btn1, col_btn2 = st.columns(2)
        login_clicked = col_btn1.button("Sign in")
        logout_clicked = col_btn2.button("Sign out", type="secondary")

        if logout_clicked:
            st.session_state.logged_in = False
            st.session_state.company_id = None

        if login_clicked:
            cid = company_input.strip()
            stored_code = COMPANY_CODES.get(cid)
            if not cid or stored_code is None:
                st.error("Unknown company ID.")
            elif not access_code:
                st.error("Access code is required.")
            elif stored_code != access_code:
                st.error("Invalid access code.")
            else:
                st.session_state.logged_in = True
                st.session_state.company_id = cid
                st.session_state.last_activity = datetime.utcnow()
                st.success("Login successful.")

        if SUPABASE_ENABLED and not PERSISTENCE_ENABLED:
            st.warning(
                "Supabase is configured, but COMPANY_CODES are not. "
                "History storage is disabled for safety."
            )
        elif not SUPABASE_ENABLED:
            st.info(
                "Supabase is not configured in secrets. "
                "The radar works, but no assessments will be stored."
            )

# If not logged in (in secure mode), stop here
if not st.session_state.logged_in:
    st.header("Defence Readiness Radar")
    st.markdown(
        """
This tool helps Defence and dual-use companies assess their **readiness level**
across five dimensions: Product, Market, Documentation, Security and Certifications.

Please sign in using the sidebar to access your company profile.
"""
    )
    st.stop()

company_id: str = st.session_state.company_id or "DEMO"

st.header("Defence Readiness Radar")
st.markdown(
    "Use the sliders below to rate your organisation. "
    "Scale: **1 = very weak**, **5 = very strong / Defence-ready**."
)
st.markdown(f"#### Company: **{company_id}**")


# -----------------------------------------------------------------------------
# Questionnaire + radar
# -----------------------------------------------------------------------------

col_left, col_right = st.columns([2.3, 1.7])

dimension_scores: Dict[str, float] = {}

with col_left:
    st.subheader("Readiness questionnaire")

    for dim_name, questions in DIMENSIONS.items():
        with st.expander(dim_name, expanded=True):
            total = 0
            for i, q in enumerate(questions, start=1):
                slider_key = f"{company_id}_{dim_name}_{i}"
                value = st.slider(
                    q,
                    min_value=1,
                    max_value=5,
                    value=3,
                    step=1,
                    key=slider_key,
                    help="1 = very weak · 5 = very strong / Defence-ready",
                )
                total += value

            avg = round(total / len(questions), 2)
            dimension_scores[dim_name] = avg

            tag_class = score_tag_class(avg)
            label = interpret_score(avg)
            st.markdown(
                f"**Average in _{dim_name}_:** {avg} "
                f"<span class='tag {tag_class}'>{label}</span>",
                unsafe_allow_html=True,
            )

overall = round(sum(dimension_scores.values()) / len(dimension_scores), 2)

with col_right:
    st.subheader("Readiness radar")

    labels = list(DIMENSIONS.keys())
    values = [dimension_scores[d] for d in labels]
    labels_closed = labels + [labels[0]]
    values_closed = values + [values[0]]

    fig = go.Figure(
        data=go.Scatterpolar(
            r=values_closed,
            theta=labels_closed,
            fill="toself",
            name="Readiness",
            line=dict(color="seagreen", width=3),
            marker=dict(size=6),
        )
    )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 5],
                tickvals=[0, 1, 2, 3, 4, 5],
            )
        ),
        showlegend=False,
        margin=dict(l=10, r=10, t=10, b=10),
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Dimension scores")
    metric_cols = st.columns(len(dimension_scores) + 1)
    for idx, (dim, score) in enumerate(dimension_scores.items()):
        metric_cols[idx].metric(dim, f"{score:.2f}", interpret_score(score))
    metric_cols[-1].metric("Overall", f"{overall:.2f}", interpret_score(overall))

    st.markdown("---")
    st.markdown(
        f"**Overall readiness score:** {overall} · **{interpret_score(overall)}**"
    )


# -----------------------------------------------------------------------------
# Persistence: save + history (only when securely enabled)
# -----------------------------------------------------------------------------


def save_assessment(scores: Dict[str, float], overall_score: float) -> None:
    """Save current assessment for the logged-in company."""
    if not PERSISTENCE_ENABLED or company_id == "DEMO":
        return

    data = {
        "company_id": company_id,
        "overall": overall_score,
        "scores": scores,
        "created_at": datetime.utcnow().isoformat(),
    }
    supabase.table("assessments").insert(data).execute()


def load_history() -> List[Dict[str, Any]]:
    """Load all saved assessments for the logged-in company."""
    if not PERSISTENCE_ENABLED or company_id == "DEMO":
        return []

    res = (
        supabase.table("assessments")
        .select("*")
        .eq("company_id", company_id)
        .order("created_at", desc=False)
        .execute()
    )
    return res.data or []


st.markdown("### Actions")

save_col, _ = st.columns([1, 3])
if save_col.button(
    "💾 Save this assessment",
    type="primary",
    disabled=not PERSISTENCE_ENABLED or company_id == "DEMO",
):
    if PERSISTENCE_ENABLED and company_id != "DEMO":
        save_assessment(dimension_scores, overall)
        st.success("Assessment saved to history.")
    elif not AUTH_ENABLED:
        st.warning("History is disabled in demo mode (no company codes configured).")
    elif not SUPABASE_ENABLED:
        st.warning("Supabase is not configured; nothing was saved.")
    else:
        st.warning("History storage is currently disabled for this deployment.")


# History / evolution chart
if PERSISTENCE_ENABLED and company_id != "DEMO":
    st.markdown("### Evolution over time")

    history = load_history()
    if not history:
        st.info("No previous assessments found for this company.")
    else:
        dates = [h["created_at"] for h in history]

        fig_hist = go.Figure()
        for dim in DIMENSIONS.keys():
            fig_hist.add_trace(
                go.Scatter(
                    x=dates,
                    y=[h["scores"].get(dim, None) for h in history],
                    mode="lines+markers",
                    name=dim,
                )
            )

        fig_hist.add_trace(
            go.Scatter(
                x=dates,
                y=[h["overall"] for h in history],
                mode="lines+markers",
                name="Overall",
                line=dict(width=4, dash="dot"),
            )
        )

        fig_hist.update_layout(
            xaxis_title="Date",
            yaxis_title="Score (0–5)",
            yaxis=dict(range=[0, 5]),
            margin=dict(l=10, r=10, t=10, b=10),
        )

        st.plotly_chart(fig_hist, use_container_width=True)
elif AUTH_ENABLED and SUPABASE_ENABLED:
    st.info(
        "History is only available for authenticated companies. "
        "Demo sessions do not create or show historical data."
    )
