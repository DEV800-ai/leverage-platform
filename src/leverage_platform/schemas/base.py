"""Base types: tenant identity envelope."""

from __future__ import annotations

from pydantic import BaseModel

type TenantId = str


class Tenant(BaseModel):
    """Tenant identity envelope.

    The platform carries `id` opaquely and never issues, validates, or
    enforces row-level isolation against it. See ADR-001.
    """

    id: TenantId
