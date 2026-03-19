import streamlit as st
from auth.auth_utils import sign_up
from pages.ui_helpers import apply_global_styles, go_to


def render():
    apply_global_styles()

    if st.session_state.get("logged_in"):
        go_to("dashboard")

    _, center, _ = st.columns([1, 2, 1])

    with center:
        st.markdown("<div class='rfp-card'>", unsafe_allow_html=True)

        st.markdown(
            "<p class='rfp-heading'>Create Account</p>"
            "<p class='rfp-subheading'>"
            "Join Venuebase RFP Auto-Responder</p>",
            unsafe_allow_html=True,
        )
        with st.form(key="signup_form", clear_on_submit=False):
            username = st.text_input(
                "Username",
                placeholder="choose_a_username",
                autocomplete="username",
            )
            email = st.text_input(
                "Email address",
                placeholder="you@company.com",
                autocomplete="email",
            )
            password = st.text_input(
                "Password",
                type="password",
                placeholder="At least 6 characters",
                autocomplete="new-password",
            )
            confirm_password = st.text_input(
                "Confirm Password",
                type="password",
                placeholder="Repeat your password",
                autocomplete="new-password",
            )

            submitted = st.form_submit_button(
                "Create Account",
                use_container_width=True,
                type="primary",
            )

        if submitted:
            error = None

            if not username or not email or not password or not confirm_password:
                error = "All fields are required."
            elif len(username.strip()) < 3:
                error = "Username must be at least 3 characters."
            elif password != confirm_password:
                error = "Passwords do not match."
            elif len(password) < 6:
                error = "Password must be at least 6 characters."

            if error:
                st.error(error)
            else:
                with st.spinner("Creating your account..."):
                    result = sign_up(
                        username=username.strip(),
                        email=email.strip().lower(),
                        password=password,
                    )

                if result["success"]:
                    st.success(result["message"])
                    st.info("Redirecting to login...")
                    st.session_state["prefill_username"] = username.strip()
                    go_to("login")
                else:
                    st.error(result["message"])

        st.markdown("<hr class='rfp-divider'>", unsafe_allow_html=True)

        st.markdown(
            "<p style='text-align:center;color:#666;font-size:0.9rem;'>"
            "Already have an account?</p>",
            unsafe_allow_html=True,
        )

        if st.button(
            " Back to Sign In",
            use_container_width=True,
            key="goto_login",
        ):
            go_to("login")

        st.markdown("</div>", unsafe_allow_html=True)