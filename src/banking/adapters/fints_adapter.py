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

# Known FinTS/HBCI Server Endpoints for major German Banks
KNOWN_FINTS_URLS = {
    "12030000": "https://fints.banking-dkb.de/fints/",      # DKB (Deutsche Kreditbank)
    "10070024": "https://fints.deutsche-bank.de/fints",     # Deutsche Bank
    "37010060": "https://hbci.postbank.de/hbci",            # Postbank
    "50010517": "https://fints.ing.de/fints/",               # ING
    "10040000": "https://fints.commerzbank.de/fints/",      # Commerzbank
    "70020270": "https://hbci-01.hypovereinsbank.de/hbci",   # HypoVereinsbank
}


class FinTSAdapter(BankAdapter):
    """Bank adapter using the FinTS/HBCI protocol for German banks.

    Supports automatic pushTAN / Decoupled 2FA challenge initiation on mobile banking apps.
    """

    def _resolve_url(self, bank_blz: str, fints_url: str) -> str:
        if not fints_url or "example.com" in fints_url or "localhost" in fints_url:
            return KNOWN_FINTS_URLS.get(bank_blz, "https://fints.banking-dkb.de/fints/")
        return fints_url

    def _create_client(
        self, bank_blz: str, fints_url: str, login_name: str, pin: str
    ) -> Any:
        """Create a FinTS3PinTanClient (synchronous, run in thread)."""
        from fints.client import FinTS3PinTanClient

        resolved_url = self._resolve_url(bank_blz, fints_url)
        logger.info("Initializing FinTS client for BLZ %s at %s", bank_blz, resolved_url)

        return FinTS3PinTanClient(
            bank_blz,
            login_name,
            pin,
            resolved_url,
            customer_id=login_name,
            product_id=settings.fints_product_id or "9FA6681DEC0593B6D87093202",
        )

    def _configure_tan_mechanism(self, client: Any) -> None:
        """Auto-configure pushTAN or Decoupled 2FA mechanism for DKB / German banks."""
        try:
            tan_mechs = client.get_tan_mechanisms()
            if not tan_mechs:
                return

            push_mech_id = None
            for sec_func, param in tan_mechs.items():
                name = getattr(param, "name", "") or str(param)
                logger.info("Bank TAN mechanism available: %s -> %s", sec_func, name)
                # DKB / German pushTAN methods (e.g. 921, 922, pushTAN, Decoupled, DKB-Code)
                name_lower = name.lower()
                if "push" in name_lower or "app" in name_lower or "code" in name_lower or "decoupled" in name_lower or sec_func in ("921", "922", "911"):
                    push_mech_id = sec_func
                    break

            if not push_mech_id:
                push_mech_id = list(tan_mechs.keys())[0]

            logger.info("Selected TAN mechanism ID: %s", push_mech_id)
            client.set_tan_mechanism(push_mech_id)

            # Try setting registered TAN medium (e.g., iPhone / device name)
            try:
                media = client.get_tan_media()
                if media:
                    medium_name = media[0][0] if isinstance(media[0], (tuple, list)) else media[0]
                    logger.info("Selecting TAN medium: %s", medium_name)
                    client.set_tan_medium(medium_name)
            except Exception as me:
                logger.debug("TAN media selection note: %s", me)

        except Exception as e:
            logger.warning("Auto-configuring TAN mechanism note: %s", e)

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

            # Configure pushTAN / Decoupled 2FA mechanism
            await asyncio.to_thread(self._configure_tan_mechanism, client)

            # Check for TAN requirement
            if client.init_tan_response:
                tan_response = client.init_tan_response
                challenge_msg = getattr(tan_response, "challenge", "Please approve login in your DKB Banking App on your iPhone")
                return AuthResult(
                    success=True,
                    requires_tan=True,
                    tan_challenge=challenge_msg,
                    tan_type="pushTAN / App Approval",
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
        """Submit TAN or confirm App approval to the bank."""
        try:
            client = session_data["client"]
            tan_response = session_data.get("tan_response")

            if tan_response:
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

            target_account = None
            for acc in sepa_accounts:
                if getattr(acc, "iban", "") == iban:
                    target_account = acc
                    break

            if target_account is None:
                logger.warning("Account with IBAN %s not found", iban)
                return []

            statements = await asyncio.to_thread(
                client.get_statement, target_account, since, date.today()
            )

            transactions = []
            for stmt in statements:
                tx_date = getattr(stmt.data, "date", None) or getattr(stmt, "date", since)
                amount = getattr(stmt.data, "amount", None) or getattr(stmt, "amount", None)
                if amount is None:
                    continue

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
