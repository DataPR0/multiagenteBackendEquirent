import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from app.config import settings
from app.utilities.logger import logger
from app.templates.email import (
    password_reset, account_activation
)


cd = os.path.dirname(os.path.abspath(__file__))


def send_account_activation_email(email: str, token: str) -> None:
    # Send the message via our SMTP server
    try:
        # Load the HTML template
        html_content = account_activation.get_template(f"{settings.front_url}/activate-account?token={token}")
        if not html_content:
            logger.error("Invalid activation link")
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Activar cuenta - Multiagente"
        msg["From"] = settings.smtp_sender
        msg["To"] = email
        msg.attach(MIMEText(html_content, 'html'))

        # Attach first logo (Equirent)
        with open(cd + "/../templates/email/images/logo.png", "rb") as png_file:
            logo_image = MIMEImage(png_file.read())
            logo_image.add_header('Content-ID', '<logo>')
            msg.attach(logo_image)

        # Attach second logo (Bureau Veritas)
        with open(cd + "/../templates/email/images/bureau_veritas.png", "rb") as png_file:
            bureau_veritas_image = MIMEImage(png_file.read())
            bureau_veritas_image.add_header('Content-ID', '<logo2>')
            msg.attach(bureau_veritas_image)

        with smtplib.SMTP_SSL(settings.smtp_server, settings.smtp_port) as smtp:
            smtp.login(settings.smtp_sender, settings.smtp_password)
            smtp.sendmail(settings.smtp_sender, email, msg.as_string())
            logger.info(f"Message sent to {email}")
    except Exception as e:
        logger.error(f"Error sending email: {e}")


def send_password_reset_email(email: str, token: str) -> None:
    """
    Sends a password reset email to the user.

    This function uses an SMTP server to send a message that contains a link 
    to reset the user's password. The link includes a unique token that 
    allows verifying the user's identity and authorizing the password reset.

    Parameters:
        email (str): The email address of the user to whom the password reset email 
                     will be sent.
        token (str): A unique token included in the password reset link. This token 
                     is used to verify the validity of the reset request.

    Returns:
        None: This function does not return any value. Its purpose is to send an email.
    """
    try:
        # Load the HTML template
        html_content = password_reset.get_template(f"{settings.front_url}/reset-password?token={token}")
        if not html_content:
            logger.error("Invalid reset link")
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Restablecer contraseña - Multiagente"
        msg["From"] = settings.smtp_sender
        msg["To"] = email
        msg.attach(MIMEText(html_content, 'html'))

        # Attach first logo (Equirent)
        with open(cd + "/../templates/email/images/logo.png", "rb") as png_file:
            logo_image = MIMEImage(png_file.read())
            logo_image.add_header('Content-ID', '<logo>')
            msg.attach(logo_image)

        # Attach second logo (Bureau Veritas)
        with open(cd + "/../templates/email/images/logo2.png", "rb") as png_file:
            bureau_veritas_image = MIMEImage(png_file.read())
            bureau_veritas_image.add_header('Content-ID', '<logo2>')
            msg.attach(bureau_veritas_image)

        with smtplib.SMTP_SSL(settings.smtp_server, settings.smtp_port) as smtp:
            smtp.login(settings.smtp_sender, settings.smtp_password)
            smtp.sendmail(settings.smtp_sender, email, msg.as_string())
            logger.info(f"Message sent to {email}")
    except Exception as e:
        logger.error(f"Error sending email: {e}")
