import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
from typing import Optional, Dict, Any, List

# ---- OPTIONAL: Supabase for persistence ----
try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = Any  # type: ignore


@st.cache_resource
def get_supabase_client() -> Optional["Client"]:
    """Create Supabase client if URL and KEY are defined in st.secrets."""
    if create_client is None:
        return None

    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY")
    if not url or not key:
        return None

    return create_client(url, key)


supabase = get_supabase_client()
SUPABASE_ENABLED = supabase is not None

# ---- PAGE CONFIG & LIGHT CSS STYLING ----
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

# ---- DIMENSIONS & QUESTIONS (ENGLISH) ----

DIMENSIONS = {
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
        "Key staff received some awareness/training on cybersecurity and information protection.",
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


# ---- LOGIN (very simple) ----

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "company_id" not in st.session_state:
    st.session_state.company_id = ""

with st.sidebar:
    st.title("Company login")
    st.caption("Use a company ID (or name) and a simple access code.")
    company_input = st.text_input("Company ID / name", value=st.session_state.company_id)
    access_code = st.text_input("Access code", type="password")
    col_btn1, col_btn2 = st.columns(2)
    login_clicked = col_btn1.button("Sign in")
    logout_clicked = col_btn2.button("Sign out", type="secondary")

    if logout_clicked:
        st.session_state.logged_in = False
        st.session_state.company_id = ""

    if login_clicked and company_input.strip():
        # In a real setup you could validate access_code via Supabase "companies" table.
        st.session_state.logged_in = True
        st.session_state.company_id = company_input.strip()

    if not SUPABASE_ENABLED:
        st.info(
            "Persistent history is disabled because `SUPABASE_URL` and "
            "`SUPABASE_KEY` are not defined in Streamlit secrets. "
            "You can still use the radar, but results will not be stored."
        )

# ---- BLOCK IF NOT LOGGED IN ----

if not st.session_state.logged_in:
    st.markdown(
        """
    ### Welcome to the Defence Readiness Radar

    Please use the sidebar to **sign in with your company ID**.  
    You can use any identifier (e.g. `Acme Defence`, `Startup-123`).  
    """
    )
    st.stop()

company_id = st.session_state.company_id

st.markdown(f"#### Company: **{company_id}**")


# ---- MAIN LAYOUT ----

col_left, col_right = st.columns([2.3, 1.7])


with col_left:
    st.subheader("Readiness questionnaire")

    answers = {}
    dimension_scores = {}

    for dim_name, questions in DIMENSIONS.items():
        with st.expander(dim_name, expanded=True):
            total = 0
            for i, q in enumerate(questions, start=1):
                key = f"{dim_name}_{i}"
                value = st.slider(
                    q,
                    min_value=1,
                    max_value=5,
                    value=3,
                    step=1,
                    key=key,
                    help="1 = very weak · 5 = very strong / Defence-ready",
                )
                answers[key] = value
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


# ---- SAVE CURRENT ASSESSMENT (if Supabase is enabled) ----

def save_assessment(scores: Dict[str, float], overall_score: float) -> None:
    if not SUPABASE_ENABLED:
        return
    data = {
        "company_id": company_id,
        "overall": overall_score,
        "scores": scores,
        "created_at": datetime.utcnow().isoformat(),
    }
    supabase.table("assessments").insert(data).execute()


def load_history() -> List[Dict[str, Any]]:
    if not SUPABASE_ENABLED:
        return []
    res = supabase.table("assessments") \
        .select("*") \
        .eq("company_id", company_id) \
        .order("created_at", desc=False) \
        .execute()
    return res.data or []


st.markdown("### Actions")

save_col, _ = st.columns([1, 3])
if save_col.button("💾 Save this assessment", type="primary", disabled=not SUPABASE_ENABLED):
    if SUPABASE_ENABLED:
        save_assessment(dimension_scores, overall)
        st.success("Assessment saved to history.")
    else:
        st.warning("Supabase is not configured. Nothing was saved.")


# ---- HISTORY & EVOLUTION OVER TIME ----

if SUPABASE_ENABLED:
    st.markdown("### Evolution over time")

    history = load_history()
    if not history:
        st.info("No previous assessments found for this company.")
    else:
        # Prepare data for line chart
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



