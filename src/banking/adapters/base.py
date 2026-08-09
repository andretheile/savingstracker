"""Abstract bank adapter interface — pluggable for FinTS, CSV, and future Open Banking."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any


@dataclass
class BankAccountInfo:
    """Information about a bank account discovered during connection."""

    iban: str
    account_name: str
    currency: str = "EUR"
    account_type: str = "checking"  # checking | savings | credit


@dataclass
class RawTransaction:
    """A raw transaction fetched from the bank, before classification."""

    transaction_date: date
    value_date: date | None
    amount: Decimal
    description: str
    counterparty: str = ""
    reference: str = ""


@dataclass
class AuthResult:
    """Result of a bank connection attempt."""

    success: bool
    requires_tan: bool = False
    tan_challenge: str = ""  # Human-readable challenge text
    tan_type: str = ""  # pushTAN, smsTAN, chipTAN, etc.
    session_data: Any = None  # Opaque session data for the adapter
    error: str = ""


class BankAdapter(ABC):
    """Abstract bank adapter. Implementations handle specific banking protocols.

    All methods are async to support non-blocking execution, even though
    some underlying libraries (like python-fints) are synchronous — those
    should be wrapped in asyncio.to_thread().
    """

    @abstractmethod
    async def connect(
        self, bank_blz: str, fints_url: str, login_name: str, pin: str
    ) -> AuthResult:
        """Establish a connection to the bank.

        Returns AuthResult indicating whether TAN verification is needed.
        """
        ...

    @abstractmethod
    async def handle_tan(self, session_data: Any, tan: str) -> AuthResult:
        """Submit a TAN for 2FA challenge verification."""
        ...

    @abstractmethod
    async def fetch_accounts(self, session_data: Any) -> list[BankAccountInfo]:
        """List available accounts at this bank."""
        ...

    @abstractmethod
    async def fetch_transactions(
        self, session_data: Any, iban: str, since: date
    ) -> list[RawTransaction]:
        """Fetch transactions for a specific account since a given date."""
        ...

    @abstractmethod
    async def disconnect(self, session_data: Any) -> None:
        """Close the bank connection and clean up resources."""
        ...
