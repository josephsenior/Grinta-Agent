"""Billing service for managing user balance and Stripe integration."""

from __future__ import annotations

import os
from typing import Optional, Any
from decimal import Decimal

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    stripe = None  # type: ignore

from forge.core.logger import forge_logger as logger

# Initialize Stripe if available
if STRIPE_AVAILABLE:
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")


class BillingService:
    """Service for managing billing, payments, and subscriptions."""

    def __init__(self):
        """Initialize billing service."""
        if not STRIPE_AVAILABLE:
            self.enabled = False
            logger.warning(
                "Stripe package not installed. Billing features will be disabled. "
                "Install stripe package: pip install stripe"
            )
        else:
            self.enabled = bool(stripe.api_key)
            if not self.enabled:
                logger.warning(
                    "Stripe API key not configured. Billing features will be disabled. "
                    "Set STRIPE_SECRET_KEY environment variable to enable."
                )

    def create_checkout_session(
        self,
        user_id: str,
        amount: int,
        success_url: str,
        cancel_url: str,
    ) -> Optional[str]:
        """Create a Stripe checkout session for adding credits.

        Args:
            user_id: User ID
            amount: Amount in USD (integer, e.g., 10 for $10.00)
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect after cancelled payment

        Returns:
            Checkout session URL or None if Stripe is not configured
        """
        if not self.enabled or not STRIPE_AVAILABLE:
            logger.error("Cannot create checkout session: Stripe not configured or not available")
            return None

        try:
            # Create checkout session
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            "product_data": {
                                "name": "Forge Credits",
                                "description": f"Add ${amount}.00 to your Forge account",
                            },
                            "unit_amount": amount * 100,  # Convert to cents
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=user_id,  # Store user ID for webhook processing
                metadata={
                    "user_id": user_id,
                    "amount": str(amount),
                },
            )

            logger.info(f"Created Stripe checkout session for user {user_id}: ${amount}")
            return session.url

        except Exception as e:
            if STRIPE_AVAILABLE and hasattr(stripe, 'error') and isinstance(e, stripe.error.StripeError):
                logger.error(f"Stripe error creating checkout session: {e}")
            else:
                logger.error(f"Unexpected error creating checkout session: {e}", exc_info=True)
            return None

    def verify_webhook_signature(
        self, payload: bytes, signature: str, webhook_secret: str
    ) -> Optional[Any]:
        """Verify Stripe webhook signature.

        Args:
            payload: Raw request payload
            signature: Stripe signature header
            webhook_secret: Webhook signing secret

        Returns:
            Stripe event if valid, None otherwise
        """
        if not self.enabled or not STRIPE_AVAILABLE:
            return None

        try:
            event = stripe.Webhook.construct_event(
                payload, signature, webhook_secret
            )
            return event
        except ValueError as e:
            logger.error(f"Invalid payload in webhook: {e}")
            return None
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature in webhook: {e}")
            return None


# Global billing service instance
_billing_service: Optional[BillingService] = None


def get_billing_service() -> BillingService:
    """Get or create the global billing service instance."""
    global _billing_service
    if _billing_service is None:
        _billing_service = BillingService()
    return _billing_service

