"""Data models for EnBW mobility+ API"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TokenResponse(BaseModel):
    """OAuth2 token response from EnBW mobility+ API"""

    access_token: str
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    token_type: str
    expires_in: int
    scope: Optional[str] = None


class Location(BaseModel):
    """Geographic location of charging station"""

    latitude: float
    longitude: float


class AuthIdentifier(BaseModel):
    """Authentication identifier for charging session"""

    model_config = ConfigDict(populate_by_name=True)

    charging_card_nr: Optional[str] = Field(None, alias="chargingCardNr")
    profile_id: Optional[int] = Field(None, alias="profileId")
    charge_auth_type: Optional[str] = Field(None, alias="chargeAuthType")  # e.g., "RFID", "APP"


class ChargingHistoryEntry(BaseModel):
    """Single charging session from history"""

    model_config = ConfigDict(populate_by_name=True)

    evse_id: str = Field(alias="evseId")  # EVSE identifier (e.g., "BE*IOY*E405103")
    operator: str  # Charging station operator
    address: str  # Full address of charging station
    location: Location  # Geographic coordinates

    auth_identifier: AuthIdentifier = Field(alias="authIdentifier")  # Authentication used

    charge_plug_type: str = Field(alias="chargePlugType")  # e.g., "CCS", "TYPE_2"
    duration_in_seconds: int = Field(alias="durationInSeconds")  # Charging duration
    energy_in_kwh: float = Field(alias="energyInKwh")  # Energy charged in kWh

    # Timestamps
    started_at: str = Field(alias="startedAt")  # ISO 8601 format
    stopped_at: str = Field(alias="stoppedAt")  # ISO 8601 format
    connection_started_at: Optional[str] = Field(None, alias="connectionStartedAt")
    connection_stopped_at: Optional[str] = Field(None, alias="connectionStoppedAt")
    connection_duration_in_seconds: Optional[int] = Field(None, alias="connectionDurationInSeconds")

    # Costs
    blocking_fee_costs_in_eur: float = Field(alias="blockingFeeCostsInEur")  # Blocking fee
    charging_costs_in_eur: float = Field(alias="chargingCostsInEur")  # Charging costs
    total_discount_in_eur: float = Field(alias="totalDiscountInEur")  # Applied discounts
    total_costs_in_eur: float = Field(alias="totalCostsInEur")  # Total costs
    charging_price_per_kwh_in_cent: int = Field(alias="chargingPricePerKwhInCent")  # Price per kWh in cents


class ChargingHistoryResponse(BaseModel):
    """Response from charging history API endpoint"""

    model_config = ConfigDict(populate_by_name=True)

    charging_history_entries: list[ChargingHistoryEntry] = Field(alias="chargingHistoryEntries")


class Profile(BaseModel):
    """User profile from EnBW API"""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    end_user_id: int = Field(alias="endUserId")
    charging_account_id: str = Field(alias="chargingAccountId")
    profile_name: Optional[str] = Field(None, alias="profileName")
    active: bool
    ciam_profile: bool = Field(alias="ciamProfile")
    has_payment: bool = Field(alias="hasPayment")
    has_tariffs: bool = Field(alias="hasTariffs")
