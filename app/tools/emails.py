from jinja2 import Template

from app.integrations.mailgun import send_single_email, send_batch_email
from app.tools.email_blacklist import blacklist

def is_blacklisted(email):
    """
    Check if the email is in the blacklist.
    """
    return email.lower() in (e.lower() for e in blacklist)

def filter_blacklisted(emails):
    """
    Filter out blacklisted emails from the provided list.
    """
    return [e for e in emails if not is_blacklisted(e)]

def send_verify_code_email(first_name, email, otp_code):
    if is_blacklisted(email):
        print(f"Email {email} is blacklisted. Not sending verification email.")
        return
    
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
    if is_blacklisted(email):
        print(f"Email {email} is blacklisted. Not sending receipt email.")
        return
    
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
    if is_blacklisted(email):
        print(f"Email {email} is blacklisted. Not sending onboarding email.")
        return
    
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
    admin_emails = ["andres@johnwetmore.com", "angelo@johnwetmore.com", "leadconex@gmail.com"]
    filtered_emails = filter_blacklisted(admin_emails)
    if not filtered_emails:
        print("All admin emails are blacklisted. Not sending error email.")
        return
    
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
        to_addresses=filtered_emails,
        subject="LeadConex Error",
        template=rendered_html,
        text=rendered_text
    )


def send_welcome_email(email):
    if is_blacklisted(email):
        print(f"Email {email} is blacklisted. Not sending welcome email.")
        return
    
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


def send_new_sign_up_email(emails, campaign_name, agent_name, agent_email, agent_phone, agent_states_with_license, agent_answers):
    filtered_emails = filter_blacklisted(emails)
    if not filtered_emails:
        print("All recipient emails are blacklisted. Not sending new sign up email.")
        return
    
    with open("app/templates/agency/new-sign-up.html") as new_sign_up_html:
        new_sign_up_template = Template(new_sign_up_html.read())
        rendered_html = new_sign_up_template.render(
            campaign_name=campaign_name,
            agent_name=agent_name,
            agent_email=agent_email,
            agent_phone=agent_phone,
            agent_states_with_license=agent_states_with_license,
            agent_answers=agent_answers
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
        to_addresses=filtered_emails,
        subject="New Agent Sign Up",
        template=rendered_html,
        text=rendered_text
    )


def send_new_order_email(emails, campaign, type, amount, lead_amount, second_chance_lead_amount, agent_name):
    filtered_emails = filter_blacklisted(emails)
    if not filtered_emails:
        print("All recipient emails are blacklisted. Not sending new order email.")
        return
    
    with open("app/templates/agency/new-order.html") as new_order_html:
        new_order_template = Template(new_order_html.read())
        rendered_html = new_order_template.render(
            campaign=campaign,
            type=type,
            amount=amount,
            lead_amount=lead_amount,
            second_chance_lead_amount=second_chance_lead_amount,
            agent_name=agent_name
        )

    with open("app/templates/agency/new-order.txt") as new_order_text:
        new_order_text = new_order_text.read()
        rendered_text = new_order_template.render(
            campaign=campaign,
            type=type,
            amount=amount,
            lead_amount=lead_amount,
            second_chance_lead_amount=second_chance_lead_amount,
            agent_name=agent_name
        )

    send_batch_email(
        to_addresses=filtered_emails,
        subject="New Order",
        template=rendered_html,
        text=rendered_text
    )


def send_cancellation_email_to_agent(email, user_name, campaign_name, amount, cancellation_date):
    if is_blacklisted(email):
        print(f"Email {email} is blacklisted. Not sending cancellation email to agent.")
        return
    
    with open("app/templates/agent/subscription-cancelled.html") as cancelation_html:
        cancelation_template = Template(cancelation_html.read())
        rendered_html = cancelation_template.render(
            user_name=user_name,
            campaign_name=campaign_name,
            amount=amount,
            cancellation_date=cancellation_date
        )

    with open("app/templates/agent/subscription-cancelled.txt") as cancelation_text:
        cancelation_text = cancelation_text.read()
        rendered_text = cancelation_template.render(
            user_name=user_name,
            campaign_name=campaign_name,
            amount=amount,
            cancellation_date=cancellation_date
        )

    send_single_email(
        to_address=email,
        subject=f"Your {campaign_name} Subscription has been Canceled",
        template=rendered_html,
        text=rendered_text
    )


def send_cancellation_email_to_agency(emails, user_name, campaign_name, amount, cancellation_date):
    filtered_emails = filter_blacklisted(emails)
    if not filtered_emails:
        print("All recipient emails are blacklisted. Not sending cancellation email to agency.")
        return
    
    with open("app/templates/agency/subscription-cancelled.html") as cancelation_html:
        cancelation_template = Template(cancelation_html.read())
        rendered_html = cancelation_template.render(
            user_name=user_name,
            campaign_name=campaign_name,
            amount=amount,
            cancellation_date=cancellation_date
        )

    with open("app/templates/agency/subscription-cancelled.txt") as cancelation_text:
        cancelation_text = cancelation_text.read()
        rendered_text = cancelation_template.render(
            user_name=user_name,
            campaign_name=campaign_name,
            amount=amount,
            cancellation_date=cancellation_date
        )

    send_batch_email(
        to_addresses=filtered_emails,
        subject=f"Agent {user_name} has Canceled their Subscription",
        template=rendered_html,
        text=rendered_text
    )


def send_negative_balance_email(emails, user_name, amount):
    filtered_emails = filter_blacklisted(emails)
    if not filtered_emails:
        print("All recipient emails are blacklisted. Not sending negative balance email.")
        return
    
    with open("app/templates/negative-account-balance.html") as negative_balance_html:
        negative_balance_template = Template(negative_balance_html.read())
        rendered_html = negative_balance_template.render(
            user_name=user_name,
            amount=amount
        )

    with open("app/templates/negative-account-balance.txt") as negative_balance_text:
        negative_balance_text = negative_balance_text.read()
        rendered_text = negative_balance_template.render(
            user_name=user_name,
            amount=amount
        )

    send_batch_email(
        to_addresses=filtered_emails,
        subject=f"Agent {user_name} has a Negative Balance",
        template=rendered_html,
        text=rendered_text
    )
