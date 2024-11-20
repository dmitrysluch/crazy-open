from wsgi import app, serializer
from flask import url_for, render_template
import requests

def send_verification_email(user):
    verification_token = serializer.dumps(user.email, salt='email-confirmation')
    verification_link = url_for('verify_email', token=verification_token, _external=True)

    email_data = {
        "sender": {
            "name": "Crazy Open Team",
            "email": "noreply@crazy-open.com"
        },
        "to": [
            {
                "email": user.email,
                "name": user.username
            }
        ],
        "subject": "Crazy Open Email Verification",
        "htmlContent": render_template("email.html", user=user, verification_link=verification_link)
    }

    headers = {
        "accept": "application/json",
        "api-key": app.config['BREVO_API_KEY'],
        "content-type": "application/json"
    }

    response = requests.post("https://api.brevo.com/v3/smtp/email", json=email_data, headers=headers)
    response.raise_for_status()