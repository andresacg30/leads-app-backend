from jinja2 import Template

from app.integrations.mailgun import send_single_email, send_batch_email


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


def send_error_to_admin(error_message):
    with open("app/templates/error-to-admin.html") as error_html:
        error_template = Template(error_html.read())
        rendered_html = error_template.render(
            error_message=error_message
        )

    with open("app/templates/error-to-admin.txt") as error_text:
        error_text = error_text.read()
        rendered_text = error_template.render(
            error_message=error_message
        )

    send_batch_email(
        to_addresses=["andres@johnwetmore.com", "angelo@johnwetmore.com", "leadconex@gmail.com"],
        subject="LeadConex Error",
        template=rendered_html,
        text=rendered_text
    )


def send_welcome_email(email):
    with open("app/templates/agent/welcome-email.html") as welcome_html:
        welcome_template = Template(welcome_html.read())
        rendered_html = welcome_template.render()

    with open("app/templates/agent/welcome-email.txt") as welcome_text:
        welcome_text = welcome_text.read()
        rendered_text = welcome_template.render()

    send_single_email(
        to_address=email,
        subject="Welcome to your Lead Dashboard!",
        template=rendered_html,
        text=rendered_text
    )


def send_new_sign_up_email(emails, campaign_name, agent_name, agent_email, agent_phone, agent_states_with_license):
    with open("app/templates/agency/new-sign-up.html") as new_sign_up_html:
        new_sign_up_template = Template(new_sign_up_html.read())
        rendered_html = new_sign_up_template.render(
            campaign_name=campaign_name,
            agent_name=agent_name,
            agent_email=agent_email,
            agent_phone=agent_phone,
            agent_states_with_license=agent_states_with_license
        )

    with open("app/templates/agency/new-sign-up.txt") as new_sign_up_text:
        new_sign_up_text = new_sign_up_text.read()
        rendered_text = new_sign_up_template.render(
            campaign_name=campaign_name,
            agent_name=agent_name,
            agent_email=agent_email,
            agent_phone=agent_phone,
            agent_states_with_license=agent_states_with_license
        )

    send_batch_email(
        to_addresses=emails,
        subject="New Agent Sign Up",
        template=rendered_html,
        text=rendered_text
    )


def send_new_order_email(emails, campaign, type, amount, lead_amount, second_chance_lead_amount):
    with open("app/templates/agency/new-order.html") as new_order_html:
        new_order_template = Template(new_order_html.read())
        rendered_html = new_order_template.render(
            campaign=campaign,
            type=type,
            amount=amount,
            lead_amount=lead_amount,
            second_chance_lead_amount=second_chance_lead_amount
        )

    with open("app/templates/agency/new-order.txt") as new_order_text:
        new_order_text = new_order_text.read()
        rendered_text = new_order_template.render(
            campaign=campaign,
            type=type,
            amount=amount,
            lead_amount=lead_amount,
            second_chance_lead_amount=second_chance_lead_amount
        )

    send_batch_email(
        to_addresses=emails,
        subject="New Order",
        template=rendered_html,
        text=rendered_text
    )
