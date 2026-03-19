import streamlit as st
from auth.auth_utils import get_user_projects, create_project, delete_project
from pages.ui_helpers import apply_global_styles, nav_bar, go_to


def render():
    apply_global_styles()
    nav_bar()

    st.markdown("##My RFP Projects")
    st.markdown(
        "Each project represents one client questionnaire run. "
        "Start a new project to upload documents and generate answers."
    )

    with st.expander("Start a New Project", expanded=True):
        with st.form("new_project_form", clear_on_submit=True):
            project_name = st.text_input(
                "Project Name",
                placeholder='e.g. "Google 2026 Annual Retreat RFP"',
            )
            create_btn = st.form_submit_button(
                "Create Project",
                type="primary",
                use_container_width=True,
            )

        if create_btn:
            if not project_name.strip():
                st.error("Please enter a project name.")
            else:
                with st.spinner("Creating project..."):
                    pid = create_project(
                        user_id=st.session_state["user_id"],
                        project_name=project_name.strip(),
                    )
                st.session_state["current_project_id"] = pid
                st.success(f"Project '{project_name}' created!")
                go_to("project")

    st.markdown("---")

    st.markdown("### Previous Projects")

    projects = get_user_projects(st.session_state["user_id"])

    if not projects:
        st.info(
            "No projects yet. Create one above to get started."
        )
        return

    for proj in projects:
        col_name, col_date, col_status, col_open, col_del = st.columns(
            [4, 2, 2, 1, 1]
        )

        with col_name:
            st.markdown(f"**{proj['project_name']}**")

        with col_date:
            created = proj.get("created_at")
            if created:
                st.caption(created.strftime("%d %b %Y, %H:%M"))

        with col_status:
            status = proj.get("status", "in_progress")
            if status == "completed":
                st.markdown(
                    "<span class='badge-answered'>✓ Completed</span>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<span class='badge-not-found'>⏳ In Progress</span>",
                    unsafe_allow_html=True,
                )

        with col_open:
            if st.button("Open", key=f"open_{proj['_id']}"):
                st.session_state["current_project_id"] = proj["_id"]
                go_to("project")

        with col_del:
            if st.button("Delete", key=f"del_{proj['_id']}", help="Delete project"):
                delete_project(proj["_id"])
                st.rerun()
