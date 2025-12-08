from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import plotly.graph_objects as go
import streamlit as st

# Supabase
try:
    from supabase import Client, create_client  # type: ignore
except ImportError:
    Client = Any  # type: ignore
    create_client = None  # type: ignore


# -----------------------------------------------------------------------------
# Page config
# -----------------------------------------------------------------------------

st.set_page_config(
    page_title="Defence Readiness Radar",
    page_icon="🛡️",
    layout="wide",
)

st.title("Defence Readiness Radar")
st.caption(
    "Self-assessment tool for Defence and dual-use companies. "
    "Scale: 1 = very weak, 5 = very strong / Defence-ready."
)


# -----------------------------------------------------------------------------
# Supabase client
# -----------------------------------------------------------------------------

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


# -----------------------------------------------------------------------------
# Questionnaire
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


# -----------------------------------------------------------------------------
# Session state for auth
# -----------------------------------------------------------------------------

if "user" not in st.session_state:
    st.session_state.user = None  # dict from Supabase user
if "company_name" not in st.session_state:
    st.session_state.company_name = None


def set_user(user: Any):
    """Store user info in session_state."""
    if user is None:
        st.session_state.user = None
        st.session_state.company_name = None
    else:
        # user.user_metadata may contain {"company_name": "..."}
        meta = getattr(user, "user_metadata", {}) or {}
        st.session_state.user = {
            "id": str(user.id),
            "email": user.email,
            "company_name": meta.get("company_name"),
        }
        st.session_state.company_name = st.session_state.user["company_name"]


# -----------------------------------------------------------------------------
# Auth UI (signup / login)
# -----------------------------------------------------------------------------

with st.sidebar:
    st.header("Account")

    if not SUPABASE_ENABLED:
        st.error("Supabase is not configured. Contact the administrator.")
    else:
        mode = st.radio("I want to…", ["Log in", "Create an account"], key="auth_mode")

        # Logged in
        if st.session_state.user:
            st.success(
                f"Logged in as {st.session_state.user['email']} "
                f"({st.session_state.company_name or 'no company name'})"
            )
            if st.button("Log out"):
                try:
                    supabase.auth.sign_out()
                except Exception:
                    pass
                set_user(None)
                st.experimental_rerun()

        # Sign up
        elif mode == "Create an account":
            st.subheader("Sign up")
            signup_email = st.text_input("Work email")
            signup_company = st.text_input("Company name")
            signup_password = st.text_input("Password", type="password")
            signup_password2 = st.text_input("Confirm password", type="password")

            if st.button("Create account"):
                if not signup_email or not signup_password or not signup_company:
                    st.error("Email, company name and password are required.")
                elif signup_password != signup_password2:
                    st.error("Passwords do not match.")
                else:
                    try:
                        result = supabase.auth.sign_up(
                            {
                                "email": signup_email,
                                "password": signup_password,
                                "options": {
                                    "data": {"company_name": signup_company}
                                },
                            }
                        )
                        # If email confirmation is ON, result.user may be None
                        if result.user is None:
                            st.success(
                                "Account created. Please check your email to confirm "
                                "your address, then log in."
                            )
                        else:
                            st.success(
                                "Account created. You can now log in with your email and password."
                            )
                    except Exception as e:  # pragma: no cover
                        st.error(f"Sign-up error: {e}")

        # Log in
        else:
            st.subheader("Log in")
            login_email = st.text_input("Email")
            login_password = st.text_input("Password", type="password")

            if st.button("Log in"):
                try:
                    result = supabase.auth.sign_in_with_password(
                        {"email": login_email, "password": login_password}
                    )
                    user = result.user
                    if user is None:
                        st.error("Invalid credentials or email not confirmed yet.")
                    else:
                        set_user(user)
                        st.experimental_rerun()
                except Exception as e:  # pragma: no cover
                    st.error(f"Login error: {e}")


# If not logged in, stop here (we already showed forms in sidebar)
if not st.session_state.user:
    st.info("Please log in or create an account using the sidebar.")
    st.stop()

user_id = st.session_state.user["id"]  # this will be a string
company_name = st.session_state.company_name or "(no company name set)"

st.markdown(f"### Company: **{company_name}**")


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
                slider_key = f"{user_id}_{dim_name}_{i}"
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
            st.write(f"Average in **{dim_name}**: {avg} ({interpret_score(avg)})")

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
    st.write(
        f"**Overall readiness score:** {overall} "
        f"(**{interpret_score(overall)}**)"
    )


# -----------------------------------------------------------------------------
# Persistence: save + history (RLS with user_id as TEXT)
# -----------------------------------------------------------------------------

def save_assessment(scores: Dict[str, float], overall_score: float) -> None:
    """Save current assessment for the logged-in user."""
    if not SUPABASE_ENABLED:
        return

    uid = str(user_id)  # ensure string for text column
    data = {
        "user_id": uid,
        "overall": overall_score,
        "scores": scores,
        "created_at": datetime.utcnow().isoformat(),
    }
    supabase.table("assessments").insert(data).execute()


def load_history() -> List[Dict[str, Any]]:
    """Load all saved assessments for the logged-in user."""
    if not SUPABASE_ENABLED:
        return []

    uid = str(user_id)
    res = (
        supabase.table("assessments")
        .select("*")
        .eq("user_id", uid)          # explicit filter, RLS adds another layer
        .order("created_at", desc=False)
        .execute()
    )
    return res.data or []


st.markdown("### Actions")

save_col, _ = st.columns([1, 3])
if save_col.button("💾 Save this assessment", type="primary"):
    if SUPABASE_ENABLED:
        try:
            save_assessment(dimension_scores, overall)
            st.success("Assessment saved to history.")
        except Exception as e:  # pragma: no cover
            st.error(f"Error saving assessment: {e}")
    else:
        st.warning("Supabase is not configured; nothing was saved.")


if SUPABASE_ENABLED:
    st.markdown("### Evolution over time")

    history = load_history()
    if not history:
        st.info("No previous assessments found for this account.")
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
