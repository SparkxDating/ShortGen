from fastapi import APIRouter, Depends

from apps.api.auth.dependencies import get_current_user
from apps.api.models.user import User
from apps.api.services import integrations_service, provider_keys_service
from apps.api.services.integrations_service import (
    SocialSettings,
    SocialSettingsUpdate,
    StripeSettings,
    StripeSettingsUpdate,
)
from apps.api.services.provider_keys_service import ProviderKeysResponse, ProviderKeysUpdate

router = APIRouter()


@router.get("/keys", response_model=ProviderKeysResponse)
def get_provider_keys(current_user: User = Depends(get_current_user)) -> ProviderKeysResponse:
    return provider_keys_service.status()


@router.put("/keys", response_model=ProviderKeysResponse)
def put_provider_keys(
    payload: ProviderKeysUpdate,
    current_user: User = Depends(get_current_user),
) -> ProviderKeysResponse:
    return provider_keys_service.update(payload)


@router.get("/social", response_model=SocialSettings)
def get_social(current_user: User = Depends(get_current_user)) -> SocialSettings:
    return integrations_service.social_status()


@router.put("/social", response_model=SocialSettings)
def put_social(
    payload: SocialSettingsUpdate,
    current_user: User = Depends(get_current_user),
) -> SocialSettings:
    return integrations_service.update_social(payload)


@router.get("/stripe", response_model=StripeSettings)
def get_stripe(current_user: User = Depends(get_current_user)) -> StripeSettings:
    return integrations_service.stripe_status()


@router.put("/stripe", response_model=StripeSettings)
def put_stripe(
    payload: StripeSettingsUpdate,
    current_user: User = Depends(get_current_user),
) -> StripeSettings:
    return integrations_service.update_stripe(payload)
