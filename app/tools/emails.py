from jinja2 import Template

from app.integrations.mailgun import send_single_email


def send_verify_code_email(first_name, email, otp_code):
    with open("app/templates/otp-code.html") as activate_account_html:
        activate_account_template = Template(activate_account_html.read())
        rendered_html = activate_account_template.render(
            user_name=first_name,
            otp_code=otp_code
        )

    with open("app/templates/otp-code.txt") as activate_account_text:
        activate_account_text = activate_account_text.read()
        rendered_text = activate_account_template.render(
            user_name=first_name,
            otp_code=otp_code
        )

    send_single_email(
        to_address=email,
        subject="Your One-Time Code",
        template=rendered_html,
        text=rendered_text
    )
