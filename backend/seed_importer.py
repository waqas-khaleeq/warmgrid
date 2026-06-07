import csv
import io
import re


PROVIDER_IMAP = {
    "gmail": {"host": "imap.gmail.com", "port": 993},
    "outlook": {"host": "outlook.office365.com", "port": 993},
    "yahoo": {"host": "imap.mail.yahoo.com", "port": 993},
    "other": {"host": "", "port": 993},
}

PROVIDER_SMTP = {
    "gmail": {"host": "smtp.gmail.com", "port": 587},
    "outlook": {"host": "smtp.office365.com", "port": 587},
    "yahoo": {"host": "smtp.mail.yahoo.com", "port": 587},
    "other": {"host": "", "port": 587},
}

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def detect_provider(email_address: str) -> str:
    domain = email_address.split("@")[-1].lower()
    if "gmail" in domain:
        return "gmail"
    if "outlook" in domain or "hotmail" in domain or "live" in domain or "office365" in domain or "microsoft" in domain:
        return "outlook"
    if "yahoo" in domain:
        return "yahoo"
    return "other"


def get_imap_settings(provider: str) -> dict:
    return PROVIDER_IMAP.get(provider, PROVIDER_IMAP["other"])


def get_smtp_settings(provider: str) -> dict:
    return PROVIDER_SMTP.get(provider, PROVIDER_SMTP["other"])


def parse_csv(file_content: str) -> dict:
    rows = []
    errors = []
    try:
        reader = csv.DictReader(io.StringIO(file_content.strip()))
        for i, row in enumerate(reader, start=2):
            email_val = (row.get("email") or row.get("Email") or "").strip()
            password_val = (row.get("app_password") or row.get("App Password") or row.get("password") or "").strip()
            provider_val = (row.get("provider") or row.get("Provider") or "").strip().lower()

            if not email_val:
                errors.append({"row": i, "email": email_val, "error": "Missing email"})
                continue
            if not EMAIL_REGEX.match(email_val):
                errors.append({"row": i, "email": email_val, "error": "Invalid email format"})
                continue
            if not password_val:
                errors.append({"row": i, "email": email_val, "error": "Missing app_password"})
                continue

            detected_provider = provider_val if provider_val in ("gmail", "outlook", "yahoo") else detect_provider(email_val)
            imap = get_imap_settings(detected_provider)
            smtp = get_smtp_settings(detected_provider)

            rows.append({
                "email": email_val,
                "app_password": password_val,
                "provider": detected_provider,
                "imap_host": imap["host"],
                "imap_port": imap["port"],
                "smtp_host": smtp["host"],
                "smtp_port": smtp["port"],
            })
    except Exception as e:
        errors.append({"row": 0, "email": "", "error": f"CSV parse error: {str(e)}"})

    return {"rows": rows, "errors": errors}
