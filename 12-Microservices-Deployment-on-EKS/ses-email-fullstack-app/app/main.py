import os
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field


APP_TITLE = os.getenv("APP_TITLE", "AWS SES Email Demo")
SES_REGION = os.getenv("SES_REGION", "ap-northeast-2")
SES_FROM_EMAIL = os.getenv("SES_FROM_EMAIL", "")
SES_SUBJECT_PREFIX = os.getenv("SES_SUBJECT_PREFIX", "[EKS SES Demo]")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title=APP_TITLE)


class EmailRequest(BaseModel):
    to_email: EmailStr
    subject: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=5000)
    sender_name: str = Field(default="EKS SES Demo", max_length=80)


@app.get("/", response_class=FileResponse)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "ses-email-fullstack"}


@app.post("/api/send-email")
def send_email(payload: EmailRequest) -> dict[str, str]:
    if not SES_FROM_EMAIL:
        raise HTTPException(status_code=500, detail="SES_FROM_EMAIL is not configured")

    client = boto3.client("sesv2", region_name=SES_REGION)
    subject = f"{SES_SUBJECT_PREFIX} {payload.subject}".strip()
    text_body = (
        f"Sender: {payload.sender_name}\n"
        f"Recipient: {payload.to_email}\n\n"
        f"{payload.message}"
    )
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #111827;">
        <h2>{subject}</h2>
        <p><strong>Sender:</strong> {payload.sender_name}</p>
        <p>{payload.message.replace(chr(10), '<br />')}</p>
      </body>
    </html>
    """

    try:
        response = client.send_email(
            FromEmailAddress=SES_FROM_EMAIL,
            Destination={"ToAddresses": [payload.to_email]},
            Content={
                "Simple": {
                    "Subject": {"Data": subject},
                    "Body": {
                        "Text": {"Data": text_body},
                        "Html": {"Data": html_body},
                    },
                }
            },
        )
    except (ClientError, BotoCoreError) as exc:
        raise HTTPException(status_code=502, detail=f"SES send failed: {exc}") from exc

    return {
        "status": "sent",
        "message_id": response["MessageId"],
        "region": SES_REGION,
    }
