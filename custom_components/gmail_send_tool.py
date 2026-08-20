import re
import smtplib
from email.message import EmailMessage

from lfx.custom.custom_component.component import Component
from lfx.io import (
    MultilineInput,
    Output,
    SecretStrInput,
    StrInput,
)
from lfx.schema.message import Message

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# Header-facing fields (To, Subject) must never contain CR/LF: a value like
# "Hi\nBcc: attacker@evil.com" would inject an extra header/recipient into the
# raw SMTP message. Reject rather than strip, so the failure is visible.
CRLF_RE = re.compile(r"[\r\n]")


class GmailSendToolComponent(Component):
    display_name = "Gmail Send Tool"
    description = (
        "Sends a plain-text email through Gmail (SMTP/STARTTLS). Validates the recipient "
        "address and rejects header-injection attempts before sending. Credentials must be "
        "bound to Global Variables — never hardcode them in the flow."
    )
    name = "GmailSendTool"
    icon = "Mail"

    inputs = [
        StrInput(
            name="sender_email",
            display_name="Sender Gmail Address",
            info="Bind to a Global Variable, e.g. GMAIL_ADDRESS.",
            required=True,
        ),
        SecretStrInput(
            name="app_password",
            display_name="Gmail App Password",
            info=(
                "16-character Gmail App Password (not the account password). Requires "
                "2-Step Verification enabled on the Google account. Bind to a Global "
                "Variable, e.g. GMAIL_APP_PASSWORD."
            ),
            required=True,
        ),
        StrInput(
            name="to_email",
            display_name="Recipient Email",
            info="The customer's email address to send the reply to.",
            required=True,
            tool_mode=True,
        ),
        StrInput(
            name="subject",
            display_name="Subject",
            info="Single-line email subject.",
            required=True,
            tool_mode=True,
        ),
        MultilineInput(
            name="body",
            display_name="Body",
            info="Plain-text email body sent to the customer.",
            required=True,
            tool_mode=True,
        ),
    ]

    outputs = [
        Output(display_name="Result", name="result", method="send_email"),
    ]

    def send_email(self) -> Message:
        to_email = (self.to_email or "").strip()
        subject = (self.subject or "").strip()
        body = (self.body or "").strip()

        if not to_email or not subject or not body:
            return Message(text="Email not sent: recipient, subject, and body are all required.")

        if CRLF_RE.search(to_email) or not EMAIL_RE.match(to_email):
            return Message(text=f"Email not sent: '{to_email}' is not a valid recipient address.")

        if CRLF_RE.search(subject):
            return Message(text="Email not sent: subject must be a single line (no line breaks).")

        if not self.sender_email or not self.app_password:
            return Message(text="Email not sent: sender credentials are not configured.")

        message = EmailMessage()
        message["From"] = self.sender_email
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)

        try:
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as smtp:
                smtp.starttls()
                smtp.login(self.sender_email, self.app_password)
                smtp.send_message(message)
        except smtplib.SMTPAuthenticationError:
            return Message(
                text=(
                    "Email not sent: Gmail authentication failed. Verify GMAIL_ADDRESS and "
                    "GMAIL_APP_PASSWORD, and that 2-Step Verification + an App Password are set up."
                )
            )
        except smtplib.SMTPRecipientsRefused:
            return Message(text=f"Email not sent: '{to_email}' was refused by the mail server.")
        except (smtplib.SMTPException, OSError) as exc:
            return Message(text=f"Email not sent due to a server/connection error: {exc}")

        return Message(text=f"Email sent successfully to {to_email} with subject '{subject}'.")
