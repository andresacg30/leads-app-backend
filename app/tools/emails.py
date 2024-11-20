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


def send_one_time_purchase_receipt(receipt_url, email, user_name, amount):
    with open("app/templates/one-time-purchase-receipt.html") as receipt_html:
        receipt_template = Template(receipt_html.read())
        rendered_html = receipt_template.render(
            user_name=user_name,
            receipt_url=receipt_url
        )

    with open("app/templates/one-time-purchase-receipt.txt") as receipt_text:
        receipt_text = receipt_text.read()
        rendered_text = receipt_template.render(
            user_name=user_name,
            receipt_url=receipt_url
        )

    send_single_email(
        to_address=email,
        subject=f"Your LeadConex Receipt for your ${amount} purchase",
        template=rendered_html,
        text=rendered_text
    )


def send_stripe_onboarding_email(email, user_name, onboarding_url, campaign):
    with open("app/templates/stripe-onboarding.html") as stripe_onboarding_html:
        stripe_onboarding_template = Template(stripe_onboarding_html.read())
        rendered_html = stripe_onboarding_template.render(
            user_name=user_name,
            stripe_onboarding_url=onboarding_url,
            campaign=campaign
        )

    with open("app/templates/stripe-onboarding.txt") as stripe_onboarding_text:
        stripe_onboarding_text = stripe_onboarding_text.read()
        rendered_text = stripe_onboarding_template.render(
            user_name=user_name,
            stripe_onboarding_url=onboarding_url,
            campaign=campaign
        )

    send_single_email(
        to_address=email,
        subject="Complete your LeadConex Stripe Account Setup",
        template=rendered_html,
        text=rendered_text
    )
