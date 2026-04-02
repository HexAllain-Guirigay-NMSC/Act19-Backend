import resend
from config import Config

resend.api_key = Config.RESEND_API_KEY


def send_verification_email(email, token):
    verify_link = f"{Config.CLIENT_URL}/verify-email?token={token}"

    params = {
        "from": "onboarding@resend.dev",
        "to": [email],
        "subject": "Verify Your Account",
        "html": f"""
            <h2>Email Verification</h2>
            <p>Click the link below to verify your account:</p>
            <p><a href="{verify_link}">{verify_link}</a></p>
        """
    }

    return resend.Emails.send(params)


def send_reset_email(email, token):
    reset_link = f"{Config.CLIENT_URL}/reset-password?token={token}"

    params = {
        "from": "onboarding@resend.dev",
        "to": [email],
        "subject": "Reset Your Password",
        "html": f"""
            <h2>Reset Password</h2>
            <p>Click the link below to reset your password:</p>
            <p><a href="{reset_link}">{reset_link}</a></p>
        """
    }

    return resend.Emails.send(params)