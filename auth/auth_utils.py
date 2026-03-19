import bcrypt
import streamlit as st
from datetime import datetime
from bson import ObjectId
from db.mongo_client import get_users_collection, get_projects_collection


#  PASSWORD 

def hash_password(plain_text: str) -> str:   
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_text.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_text: str, hashed: str) -> bool:
    return bcrypt.checkpw(
        plain_text.encode("utf-8"),
        hashed.encode("utf-8")
    )


#  SIGN UP

def sign_up(username: str, email: str, password: str) -> dict:
    users_col = get_users_collection()

    # Validation
    if not username or not email or not password:
        return {"success": False, "message": "All fields are required."}

    if len(password) < 6:
        return {"success": False, "message": "Password must be at least 6 characters."}

    if "@" not in email:
        return {"success": False, "message": "Please enter a valid email address."}

    # duplicates
    existing = users_col.find_one(
        {"$or": [{"username": username}, {"email": email}]}
    )
    if existing:
        if existing.get("username") == username:
            return {"success": False, "message": "Username already taken."}
        return {"success": False, "message": "Email already registered."}

    new_user = {
        "username": username,
        "email": email,
        "password_hash": hash_password(password),
        "created_at": datetime.utcnow(),
    }
    result = users_col.insert_one(new_user)

    return {
        "success": True,
        "message": "Account created successfully! Please log in.",
        "user_id": str(result.inserted_id),
    }

#  LOG IN

def log_in(username: str, password: str) -> dict:
    users_col = get_users_collection()

    if not username or not password:
        return {"success": False, "message": "Username and password are required."}

    user = users_col.find_one({"username": username})

    if not user:
        return {"success": False, "message": "Invalid username or password."}

    if not verify_password(password, user["password_hash"]):
        return {"success": False, "message": "Invalid username or password."}

    return {
        "success": True,
        "user_id": str(user["_id"]),
        "username": user["username"],
        "email": user["email"],
    }


#  SESSION STATE HELPERS

def init_session():
    defaults = {
        "logged_in": False,
        "user_id": None,
        "username": None,
        "email": None,
        "current_project_id": None,
        "current_page": "login",      
        "answers_df": None,          
        "upload_status": None,        
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def set_logged_in(user_id: str, username: str, email: str):
    st.session_state["logged_in"] = True
    st.session_state["user_id"] = user_id
    st.session_state["username"] = username
    st.session_state["email"] = email
    st.session_state["current_page"] = "dashboard"


def log_out():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    init_session()
    st.session_state["current_page"] = "login"


def require_login():
    if not st.session_state.get("logged_in"):
        st.session_state["current_page"] = "login"
        return False
    return True


#  PROJECT CRUD
def create_project(user_id: str, project_name: str) -> str:
    projects_col = get_projects_collection()
    doc = {
        "user_id": user_id,
        "project_name": project_name,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "status": "in_progress",   
        "questions": [],           
    }
    result = projects_col.insert_one(doc)
    return str(result.inserted_id)


def save_questions_to_project(project_id: str, questions: list[dict]):
    projects_col = get_projects_collection()
    projects_col.update_one(
        {"_id": ObjectId(project_id)},
        {
            "$set": {
                "questions": questions,
                "updated_at": datetime.utcnow(),
                "status": "completed",
            }
        }
    )


def get_project(project_id: str) -> dict | None:
    projects_col = get_projects_collection()
    doc = projects_col.find_one({"_id": ObjectId(project_id)})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


def get_user_projects(user_id: str) -> list[dict]:
    projects_col = get_projects_collection()
    cursor = projects_col.find(
        {"user_id": user_id}
    ).sort("created_at", -1)

    projects = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        projects.append(doc)
    return projects


def delete_project(project_id: str):
    projects_col = get_projects_collection()
    projects_col.delete_one({"_id": ObjectId(project_id)})