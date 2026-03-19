import streamlit as st
from auth.auth_utils import log_in, set_logged_in
from pages.ui_helpers import apply_global_styles, go_to


def render():
    apply_global_styles()

    if st.session_state.get("logged_in"):
        go_to("dashboard")

    _, center, _ = st.columns([1, 2, 1])

    with center:
        st.markdown("<div class='rfp-card'>", unsafe_allow_html=True)

        st.markdown(
            "<p class='rfp-heading'> Venuebase</p>"
            "<p class='rfp-subheading'>RFP Auto-Responder — Sign in to continue</p>",
            unsafe_allow_html=True,
        )

        with st.form(key="login_form", clear_on_submit=False):
            username = st.text_input(
                "Username",
                placeholder="your_username",
                autocomplete="username",
            )
            password = st.text_input(
                "Password",
                type="password",
                placeholder="••••••••",
                autocomplete="current-password",
            )

            submitted = st.form_submit_button(
                "Sign In",
                use_container_width=True,
                type="primary",
            )

        if submitted:
            if not username or not password:
                st.error("Please enter both username and password.")
            else:
                with st.spinner("Authenticating..."):
                    result = log_in(username.strip(), password)

                if result["success"]:
                    set_logged_in(
                        user_id=result["user_id"],
                        username=result["username"],
                        email=result["email"],
                    )
                    st.success(f"Welcome back, {result['username']}!")
                    st.rerun()
                else:
                    st.error(result["message"])

        st.markdown("<hr class='rfp-divider'>", unsafe_allow_html=True)

        st.markdown(
            "<p style='text-align:center;color:#666;font-size:0.9rem;'>"
            "Don't have an account?</p>",
            unsafe_allow_html=True,
        )

        if st.button(
            "Create an account →",
            use_container_width=True,
            key="goto_signup",
        ):
            go_to("signup")

        st.markdown("</div>", unsafe_allow_html=True)