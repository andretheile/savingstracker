"""FinTS/HBCI adapter for German banks using python-fints."""

from __future__ import annotations

import asyncio
import logging
from datetime import date
from decimal import Decimal
from typing import Any

from src.banking.adapters.base import (
    AuthResult,
    BankAccountInfo,
    BankAdapter,
    RawTransaction,
)
from src.config import settings

logger = logging.getLogger(__name__)


class FinTSAdapter(BankAdapter):
    """Bank adapter using the FinTS/HBCI protocol for German banks.

    Since python-fints is a synchronous library, all calls are wrapped
    in asyncio.to_thread() to avoid blocking the event loop.
    """

    def _create_client(
        self, bank_blz: str, fints_url: str, login_name: str, pin: str
    ) -> Any:
        """Create a FinTS3PinTanClient (synchronous, run in thread)."""
        from fints.client import FinTS3PinTanClient

        return FinTS3PinTanClient(
            bank_blz,
            login_name,
            pin,
            fints_url,
            product_id=settings.fints_product_id or None,
        )

    async def connect(
        self, bank_blz: str, fints_url: str, login_name: str, pin: str
    ) -> AuthResult:
        """Establish a FinTS connection, check if TAN is needed."""
        try:
            client = await asyncio.to_thread(
                self._create_client, bank_blz, fints_url, login_name, pin
            )

            # Enter the dialog context
            dialog_data = await asyncio.to_thread(client.__enter__)

            # Check for TAN requirement
            if client.init_tan_response:
                tan_response = client.init_tan_response
                return AuthResult(
                    success=True,
                    requires_tan=True,
                    tan_challenge=getattr(tan_response, "challenge", "Please enter TAN"),
                    tan_type=getattr(
                        tan_response, "challenge_hhduc", "pushTAN"
                    ),
                    session_data={"client": client, "tan_response": tan_response},
                )

            return AuthResult(
                success=True,
                requires_tan=False,
                session_data={"client": client},
            )

        except Exception as e:
            logger.error("FinTS connection failed: %s", e)
            return AuthResult(success=False, error=str(e))

    async def handle_tan(self, session_data: Any, tan: str) -> AuthResult:
        """Submit TAN to the bank for verification."""
        try:
            client = session_data["client"]
            tan_response = session_data["tan_response"]

            await asyncio.to_thread(client.send_tan, tan_response, tan)

            return AuthResult(
                success=True,
                requires_tan=False,
                session_data=session_data,
            )
        except Exception as e:
            logger.error("TAN verification failed: %s", e)
            return AuthResult(success=False, error=str(e))

    async def fetch_accounts(self, session_data: Any) -> list[BankAccountInfo]:
        """Fetch SEPA accounts from the bank."""
        try:
            client = session_data["client"]
            sepa_accounts = await asyncio.to_thread(client.get_sepa_accounts)

            accounts = []
            for acc in sepa_accounts:
                accounts.append(
                    BankAccountInfo(
                        iban=getattr(acc, "iban", ""),
                        account_name=getattr(acc, "accountnumber", "Account"),
                        currency=getattr(acc, "currency", "EUR"),
                    )
                )
            return accounts

        except Exception as e:
            logger.error("Failed to fetch accounts: %s", e)
            return []

    async def fetch_transactions(
        self, session_data: Any, iban: str, since: date
    ) -> list[RawTransaction]:
        """Fetch transactions from a specific account since a given date."""
        try:
            client = session_data["client"]
            sepa_accounts = await asyncio.to_thread(client.get_sepa_accounts)

            # Find the matching account by IBAN
            target_account = None
            for acc in sepa_accounts:
                if getattr(acc, "iban", "") == iban:
                    target_account = acc
                    break

            if target_account is None:
                logger.warning("Account with IBAN %s not found", iban)
                return []

            # Fetch statements
            statements = await asyncio.to_thread(
                client.get_statement, target_account, since, date.today()
            )

            transactions = []
            for stmt in statements:
                # stmt is an mt940 transaction object
                tx_date = getattr(stmt.data, "date", None) or getattr(stmt, "date", since)
                amount = getattr(stmt.data, "amount", None) or getattr(stmt, "amount", None)
                if amount is None:
                    continue

                # Extract amount as Decimal
                if hasattr(amount, "amount"):
                    amt = Decimal(str(amount.amount))
                else:
                    amt = Decimal(str(amount))

                purpose = getattr(stmt.data, "purpose", "") or ""
                applicant = getattr(stmt.data, "applicant_name", "") or ""

                transactions.append(
                    RawTransaction(
                        transaction_date=tx_date,
                        value_date=getattr(stmt.data, "entry_date", None),
                        amount=amt,
                        description=purpose if isinstance(purpose, str) else str(purpose),
                        counterparty=applicant,
                        reference=getattr(stmt.data, "bank_reference", "") or "",
                    )
                )

            logger.info(
                "Fetched %d transactions for IBAN %s since %s",
                len(transactions), iban, since,
            )
            return transactions

        except Exception as e:
            logger.error("Failed to fetch transactions: %s", e)
            return []

    async def disconnect(self, session_data: Any) -> None:
        """Close the FinTS dialog."""
        try:
            client = session_data.get("client")
            if client:
                await asyncio.to_thread(client.__exit__, None, None, None)
        except Exception as e:
            logger.warning("Error disconnecting FinTS client: %s", e)
