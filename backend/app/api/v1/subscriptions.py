from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from stripe import SignatureVerificationError

from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.persistent_user import PersistentUserNotFoundError, resolve_existing_persistent_user
from app.auth.schemas import AuthUser
from app.core.config import settings
from app.database.session import get_db
from app.models.application_entitlement import EntitlementStatus
from app.schemas.apple_subscription import (
    AppleNotificationRequest,
    AppleTransactionVerificationRequest,
    AppleWebhookResponse,
)
from app.schemas.stripe_subscription import (
    CheckoutSessionCreateRequest,
    StripeSessionResponse,
    StripeWebhookResponse,
    SubscriptionOverviewResponse,
)
from app.providers.apple_subscription_provider import (
    AppleSubscriptionConfigurationError,
    AppleSubscriptionProvider,
    AppleVerificationError,
)
from app.services.apple_subscription_service import (
    AppleSubscriptionError,
    AppleSubscriptionOwnershipError,
    process_verified_apple_notification,
    verify_and_synchronize_apple_transaction,
)
from app.services.entitlement_service import get_entitlement, has_active_entitlement
from app.services.entitlement_reconciliation_service import PREMIUM_ENTITLEMENT_KEY
from app.services.provider_subscription_service import get_user_provider_subscriptions
from app.services.stripe_gateway import StripeGateway, StripeSandboxConfigurationError
from app.services.stripe_subscription_service import (
    StripeEventProcessingError,
    create_billing_portal_session,
    create_checkout_session,
    process_verified_stripe_event,
)

router = APIRouter(
    prefix="/subscriptions",
    tags=["Subscriptions"]
)


@router.get(
    "/me",
    response_model=SubscriptionOverviewResponse,
)
def my_subscription(
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = _persistent_user(db, current_user)
    return _subscription_overview(db, user.id)


def _subscription_overview(db: Session, user_id: int):
    entitlement = get_entitlement(db, user_id, PREMIUM_ENTITLEMENT_KEY)
    subscriptions = get_user_provider_subscriptions(db, user_id)
    return {
        "entitlement_key": PREMIUM_ENTITLEMENT_KEY,
        "plan": entitlement.plan if entitlement else "free",
        "status": entitlement.status if entitlement else EntitlementStatus.INACTIVE.value,
        "active": has_active_entitlement(db, user_id, PREMIUM_ENTITLEMENT_KEY),
        "starts_at": entitlement.starts_at if entitlement else None,
        "ends_at": entitlement.ends_at if entitlement else None,
        "provider_subscriptions": subscriptions,
    }


def _persistent_user(db: Session, current_user: AuthUser):
    try:
        return resolve_existing_persistent_user(db, current_user)
    except PersistentUserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A persistent account is required for subscription billing",
        ) from exc


def _stripe_gateway(*, require_webhook_secret: bool = False) -> StripeGateway:
    try:
        return StripeGateway.from_settings(require_webhook_secret=require_webhook_secret)
    except StripeSandboxConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


def _apple_provider() -> AppleSubscriptionProvider:
    try:
        return AppleSubscriptionProvider.from_settings()
    except AppleSubscriptionConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.post("/checkout-session", response_model=StripeSessionResponse)
def checkout_session(
    payload: CheckoutSessionCreateRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = _persistent_user(db, current_user)
    gateway = _stripe_gateway()
    try:
        session = create_checkout_session(db, gateway, user=user, plan=payload.plan)
    except StripeEventProcessingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"url": session.url}


@router.post("/billing-portal", response_model=StripeSessionResponse)
def billing_portal(
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = _persistent_user(db, current_user)
    gateway = _stripe_gateway()
    try:
        session = create_billing_portal_session(db, gateway, user=user)
    except StripeEventProcessingError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return {"url": session.url}


@router.post("/webhooks/stripe", response_model=StripeWebhookResponse)
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    gateway = _stripe_gateway(require_webhook_secret=True)
    payload = await request.body()
    try:
        event = gateway.construct_webhook_event(payload, stripe_signature)
    except (SignatureVerificationError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe webhook signature",
        ) from exc
    try:
        processing_status, duplicate = process_verified_stripe_event(db, gateway, event)
    except StripeEventProcessingError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return {"status": processing_status, "duplicate": duplicate}


@router.post("/apple/verify", response_model=SubscriptionOverviewResponse)
def verify_apple_subscription(
    payload: AppleTransactionVerificationRequest,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = _persistent_user(db, current_user)
    provider = _apple_provider()
    try:
        verify_and_synchronize_apple_transaction(
            db,
            provider,
            user_id=user.id,
            signed_transaction=payload.signedTransaction,
        )
        db.commit()
    except AppleSubscriptionOwnershipError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except (AppleVerificationError, AppleSubscriptionError) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return _subscription_overview(db, user.id)


@router.post("/webhooks/apple", response_model=AppleWebhookResponse)
def apple_webhook(
    payload: AppleNotificationRequest,
    db: Session = Depends(get_db),
):
    provider = _apple_provider()
    try:
        notification = provider.verify_notification(payload.signedPayload)
    except AppleVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Apple notification signature or claims",
        ) from exc
    try:
        processing_status, duplicate = process_verified_apple_notification(
            db,
            notification,
        )
    except AppleSubscriptionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return {"status": processing_status, "duplicate": duplicate}