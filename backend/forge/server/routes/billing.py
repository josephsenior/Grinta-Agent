"""Billing API routes for payments, balance, and subscriptions."""

from __future__ import annotations

import os
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, status, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from forge.core.logger import forge_logger as logger
from forge.server.middleware.auth import get_current_user_id
from forge.server.utils.responses import success, error
from forge.server.services.billing_service import get_billing_service
from forge.storage.billing.billing_store import get_billing_store

router = APIRouter(prefix="/api/billing", tags=["billing"])


# Request/Response Models
class CreateCheckoutSessionRequest(BaseModel):
    """Request to create a Stripe checkout session."""

    amount: int = Field(..., ge=10, le=25000, description="Amount in USD (minimum $10, maximum $25,000)")


class CheckoutSessionResponse(BaseModel):
    """Response containing checkout session URL."""

    redirect_url: str


class BalanceResponse(BaseModel):
    """Response containing user balance."""

    credits: str  # Balance as string to maintain precision


class SubscriptionAccessResponse(BaseModel):
    """Response containing subscription access information."""

    status: str  # ACTIVE, DISABLED, etc.
    start_at: str
    end_at: str
    created_at: str


@router.get("/credits", response_model=BalanceResponse)
async def get_credits(
    request: Request,
    user_id: str = Depends(get_current_user_id),
) -> BalanceResponse:
    """Get user balance/credits.

    Returns:
        User's current balance in USD
    """
    try:
        billing_store = get_billing_store()
        balance = await billing_store.get_balance(user_id)
        return BalanceResponse(credits=str(balance))
    except Exception as e:
        logger.error(f"Error getting balance for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve balance",
        )


@router.post("/create-checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: Request,
    checkout_data: CreateCheckoutSessionRequest,
    user_id: str = Depends(get_current_user_id),
) -> CheckoutSessionResponse:
    """Create a Stripe checkout session for adding credits.

    Args:
        request: FastAPI request
        checkout_data: Checkout session request data
        user_id: Current user ID from auth

    Returns:
        Checkout session URL for redirect

    Raises:
        HTTPException: If Stripe is not configured or session creation fails
    """
    try:
        billing_service = get_billing_service()
        if not billing_service.enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Payment processing is not configured. Please contact support.",
            )

        # Build success and cancel URLs
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3001")
        success_url = f"{frontend_url}/settings/billing?checkout=success"
        cancel_url = f"{frontend_url}/settings/billing?checkout=cancel"

        # Create checkout session
        checkout_url = billing_service.create_checkout_session(
            user_id=user_id,
            amount=checkout_data.amount,
            success_url=success_url,
            cancel_url=cancel_url,
        )

        if not checkout_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create checkout session",
            )

        logger.info(f"Created checkout session for user {user_id}: ${checkout_data.amount}")
        return CheckoutSessionResponse(redirect_url=checkout_url)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating checkout session for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session",
        )


@router.get("/subscription-access", response_model=Optional[SubscriptionAccessResponse])
async def get_subscription_access(
    request: Request,
    user_id: str = Depends(get_current_user_id),
) -> Optional[SubscriptionAccessResponse]:
    """Get user subscription access information.

    Returns:
        Subscription access data or None if no subscription
    """
    try:
        billing_store = get_billing_store()
        subscription = await billing_store.get_subscription(user_id)

        if not subscription:
            return None

        return SubscriptionAccessResponse(
            status=subscription.get("status", "DISABLED"),
            start_at=subscription.get("start_at", ""),
            end_at=subscription.get("end_at", ""),
            created_at=subscription.get("created_at", ""),
        )
    except Exception as e:
        logger.error(f"Error getting subscription for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscription",
        )


async def _process_checkout_session_completed(event: dict, billing_store) -> None:
    """Process checkout.session.completed event."""
    session = event["data"]["object"]
    user_id = session.get("client_reference_id") or session.get("metadata", {}).get("user_id")
    amount_str = session.get("metadata", {}).get("amount", "0")

    if user_id:
        try:
            amount = Decimal(amount_str)
            await billing_store.add_balance(user_id, amount)
            logger.info(f"Processed payment: Added ${amount} to user {user_id}")
        except Exception as e:
            logger.error(f"Error processing payment for user {user_id}: {e}", exc_info=True)
    else:
        logger.warning("Payment completed but no user_id found in session")


async def _process_payment_intent_succeeded(event: dict, billing_store) -> None:
    """Process payment_intent.succeeded event."""
    payment_intent = event["data"]["object"]
    metadata = payment_intent.get("metadata", {})
    user_id = metadata.get("user_id")

    if user_id:
        try:
            # Amount is in cents, convert to dollars
            amount_cents = payment_intent.get("amount", 0)
            amount = Decimal(amount_cents) / Decimal("100")
            await billing_store.add_balance(user_id, amount)
            logger.info(f"Processed payment intent: Added ${amount} to user {user_id}")
        except Exception as e:
            logger.error(f"Error processing payment intent for user {user_id}: {e}", exc_info=True)


async def _process_stripe_event(event: dict, billing_store) -> None:
    """Process Stripe webhook event based on type."""
    event_type = event.get("type")
    
    if event_type == "checkout.session.completed":
        await _process_checkout_session_completed(event, billing_store)
    elif event_type == "payment_intent.succeeded":
        await _process_payment_intent_succeeded(event, billing_store)


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature"),
) -> JSONResponse:
    """Handle Stripe webhook events.

    This endpoint processes payment events from Stripe and updates user balances.

    Args:
        request: FastAPI request
        stripe_signature: Stripe signature header for webhook verification

    Returns:
        Success response
    """
    try:
        billing_service = get_billing_service()
        if not billing_service.enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Webhook processing is not configured",
            )

        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        if not webhook_secret:
            logger.error("STRIPE_WEBHOOK_SECRET not configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Webhook secret not configured",
            )

        if not stripe_signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing stripe-signature header",
            )

        # Get raw body
        body = await request.body()

        # Verify webhook signature
        event = billing_service.verify_webhook_signature(
            payload=body,
            signature=stripe_signature,
            webhook_secret=webhook_secret,
        )

        if not event:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook signature",
            )

        # Process the event
        billing_store = get_billing_store()
        await _process_stripe_event(event, billing_store)

        return success(message="Webhook processed", request=request)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed",
        )

