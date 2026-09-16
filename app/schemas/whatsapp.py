from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WhatsAppText(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")
    body: str


class WhatsAppMessage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore", populate_by_name=True)
    id: str
    from_: str = Field(alias="from")
    timestamp: str
    type: str
    text: WhatsAppText | None = None


class WhatsAppMetadata(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")
    display_phone_number: str
    phone_number_id: str


class WhatsAppValue(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")
    messaging_product: str
    metadata: WhatsAppMetadata
    contacts: list[dict[str, Any]] | None = None
    messages: list[WhatsAppMessage] | None = None
    statuses: list[dict[str, Any]] | None = None


class WhatsAppChange(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")
    field: str
    value: WhatsAppValue


class WhatsAppEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")
    id: str
    changes: list[WhatsAppChange]


class WhatsAppWebhook(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")
    object: str
    entry: list[WhatsAppEntry]
