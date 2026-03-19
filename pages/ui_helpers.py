import streamlit as st


def apply_global_styles():
    st.markdown(
        """
        <style>
        .rfp-card {
            background: var(--background-color, #ffffff);
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            padding: 2rem 2.5rem;
            max-width: 480px;
            margin: 2rem auto;
            box-shadow: 0 2px 12px rgba(0,0,0,0.07);
        }

        .rfp-heading {
            font-size: 1.8rem;
            font-weight: 700;
            color: #1a1a2e;
            margin-bottom: 0.25rem;
        }

        .rfp-subheading {
            font-size: 0.95rem;
            color: #555;
            margin-bottom: 1.5rem;
        }

        .metric-pill {
            border-radius: 8px;
            padding: 1rem;
            text-align: center;
            font-size: 0.85rem;
            font-weight: 600;
        }

        .rfp-divider {
            border: none;
            border-top: 1px solid #eee;
            margin: 1.2rem 0;
        }

        .badge-answered {
            color: #1a7f4b;
            background: #d4f5e2;
            border-radius: 20px;
            padding: 2px 10px;
            font-size: 0.78rem;
            font-weight: 600;
        }

        .badge-not-found {
            color: #b54708;
            background: #fde8cc;
            border-radius: 20px;
            padding: 2px 10px;
            font-size: 0.78rem;
            font-weight: 600;
        }

        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def nav_bar(show_logout: bool = True):
    col_logo, col_user, col_logout = st.columns([6, 3, 1])

    with col_logo:
        st.markdown(
            "###  Venuebase &nbsp;|&nbsp; "
            "<span style='font-weight:400;font-size:1rem;color:#666;'>"
            "RFP Responder</span>",
            unsafe_allow_html=True,
        )

    if show_logout and st.session_state.get("logged_in"):
        with col_user:
            st.markdown(
                f"<div style='text-align:right;padding-top:0.6rem;color:#555;'>"
                f" {st.session_state.get('username', '')}</div>",
                unsafe_allow_html=True,
            )
        with col_logout:
            if st.button("Log out", key="nav_logout"):
                from auth.auth_utils import log_out
                log_out()
                st.rerun()

    st.markdown("<hr class='rfp-divider'>", unsafe_allow_html=True)


def go_to(page: str):
    st.session_state["current_page"] = page
    st.rerun()