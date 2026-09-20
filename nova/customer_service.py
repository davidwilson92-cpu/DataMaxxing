"""Shared customer-facing offer and support context; never enables billing."""
import os
from . import billing
from .allowances import PLANS


def context():
    return {
        'operator_name': os.environ.get('LEGAL_ENTITY_NAME', 'Zova Social Limited'),
        'support_email': os.environ.get('SUPPORT_EMAIL') or os.environ.get('PRIVACY_CONTACT_EMAIL') or 'zova.social@gmail.com',
        'offer_catalog': PLANS,
        'offer_state': 'test' if billing.checkout_enabled() and billing.mode() == 'test' else 'live' if billing.checkout_enabled() else 'unavailable',
        'testing_access': not billing.require_subscription(),
        'metrics_enabled': os.environ.get('PRODUCT_METRICS_ENABLED','false').lower()=='true',
        'verification_required': os.environ.get('EMAIL_VERIFICATION_REQUIRED_FOR_CHECKOUT','false').lower()=='true',
    }
