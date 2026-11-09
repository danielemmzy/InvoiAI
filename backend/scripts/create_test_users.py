import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client


# Load backend/.env
BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL is missing from backend/.env")

if not SUPABASE_SERVICE_KEY:
    raise RuntimeError("SUPABASE_SERVICE_KEY is missing from backend/.env")

print(f"Supabase URL loaded: {SUPABASE_URL}")
print("Supabase service key loaded: YES")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_KEY,
)

TEST_USERS = [
    {
        "email": "admin@test.invoiai.local",
        "password": "InvoiAI_Test_Admin_2026!",
        "name": "V2 Test Admin",
    },
    {
        "email": "approver@test.invoiai.local",
        "password": "InvoiAI_Test_Approver_2026!",
        "name": "V2 Test Approver",
    },
    {
        "email": "staff@test.invoiai.local",
        "password": "InvoiAI_Test_Staff_2026!",
        "name": "V2 Test Staff",
    },
]

for test_user in TEST_USERS:
    email = test_user["email"]

    # Check whether the user already exists
    users = supabase.auth.admin.list_users()
    existing = next(
        (u for u in users if u.email == email),
        None,
    )

    if existing:
        user = existing
        print(f"EXISTS: {email} -> {user.id}")
    else:
        response = supabase.auth.admin.create_user({
            "email": email,
            "password": test_user["password"],
            "email_confirm": True,
            "user_metadata": {
                "full_name": test_user["name"],
            },
        })

        user = response.user
        print(f"CREATED: {email} -> {user.id}")

    # Create/update profile
    supabase.table("profiles").upsert({
        "id": str(user.id),
        "full_name": test_user["name"],
        "timezone": "UTC",
        "language": "en",
        "onboarding_completed": True,
        "onboarding_step": 0,
    }).execute()

    print(f"PROFILE OK: {email}")

print("\nTEST USERS READY")