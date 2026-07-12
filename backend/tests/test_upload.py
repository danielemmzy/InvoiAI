from io import BytesIO
from fastapi import status, HTTPException


def test_upload_invalid_file_type(client):
    response = client.post(
        "/upload",
        files={
            "file": (
                "malware.exe",
                BytesIO(b"fake"),
                "application/octet-stream",
            )
        },
        data={"industry": "general"},
    )

    assert response.status_code == 400
    assert "not supported" in response.json()["detail"]



def test_upload_invalid_industry(client):
    response = client.post(
        "/upload",
        files={
            "file": (
                "invoice.pdf",
                BytesIO(b"pdf"),
                "application/pdf",
            )
        },
        data={"industry": "cars"},
    )

    assert response.status_code == 400




def test_usage_limit_reached(client, mocker):

    mocker.patch(
    "app.routers.upload.check_usage_limit",
    side_effect=HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Monthly limit reached. You have used 5/5 documents.",
    ),
)

    response = client.post(
        "/upload",
        files={
            "file": (
                "invoice.pdf",
                BytesIO(b"pdf"),
                "application/pdf",
            )
        },
        data={"industry": "general"},
    )

    assert response.status_code == 429