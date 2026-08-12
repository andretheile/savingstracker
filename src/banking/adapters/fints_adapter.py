"""FinTS/HBCI adapter for German banks using python-fints."""

from __future__ import annotations

import asyncio
import logging
import time
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

DKB_FINTS_URL = "https://fints.dkb.de/fints"
_LEGACY_DKB_HOSTS = (
    "fints.banking-dkb.de",
    "banking-dkb.s-fints-pt-dkb.de",
)

# Known FinTS/HBCI Server Endpoints for major German Banks
KNOWN_FINTS_URLS = {
    "12030000": DKB_FINTS_URL,                              # DKB (Deutsche Kreditbank)
    "10070024": "https://fints.deutsche-bank.de/fints",     # Deutsche Bank
    "37010060": "https://hbci.postbank.de/hbci",            # Postbank
    "50010517": "https://fints.ing.de/fints/",               # ING
    "10040000": "https://fints.commerzbank.de/fints/",      # Commerzbank
    "70020270": "https://hbci-01.hypovereinsbank.de/hbci",   # HypoVereinsbank
}

# DKB migrated to mechanism 940 (Decoupled / DKB App) in late 2024
PREFERRED_TAN_MECHANISMS = ("940", "921", "922", "911")
DECOUPLED_POLL_INTERVAL_SECONDS = 1
DECOUPLED_POLL_MAX_ATTEMPTS = 120

# DKB returns HTTP 400 during system_id sync if the product ID is unknown.
# This public ID is accepted by DKB; register your own at
# https://www.fints.org/de/hersteller/produktregistrierung
DEFAULT_FINTS_PRODUCT_ID = "6151256F3D4F9975B877BD4A2"


class FinTSAdapter(BankAdapter):
    """Bank adapter using the FinTS/HBCI protocol for German banks.

    Supports automatic pushTAN / Decoupled 2FA challenge initiation on mobile banking apps.
    """

    def _resolve_url(self, bank_blz: str, fints_url: str) -> str:
        if fints_url and any(host in fints_url for host in _LEGACY_DKB_HOSTS):
            logger.info("Rewriting legacy DKB FinTS URL to %s", DKB_FINTS_URL)
            return DKB_FINTS_URL
        if not fints_url or "example.com" in fints_url or "localhost" in fints_url:
            return KNOWN_FINTS_URLS.get(bank_blz, DKB_FINTS_URL)
        return fints_url

    def _create_client(
        self, bank_blz: str, fints_url: str, login_name: str, pin: str
    ) -> Any:
        """Create a FinTS3PinTanClient (synchronous, run in thread)."""
        from fints.client import FinTS3PinTanClient

        resolved_url = self._resolve_url(bank_blz, fints_url)
        product_id = settings.fints_product_id or DEFAULT_FINTS_PRODUCT_ID
        logger.info(
            "Initializing FinTS client for BLZ %s at %s (product_id %s)",
            bank_blz,
            resolved_url,
            "from env" if settings.fints_product_id else "public DKB fallback",
        )

        return FinTS3PinTanClient(
            bank_blz,
            login_name,
            pin,
            resolved_url,
            customer_id=login_name,
            product_id=product_id,
        )

    def _select_tan_mechanism(self, tan_mechs: dict[Any, Any]) -> Any:
        """Pick the best TAN mechanism, preferring DKB App / decoupled (940)."""
        by_id = {str(sec_func): sec_func for sec_func in tan_mechs}
        for preferred_id in PREFERRED_TAN_MECHANISMS:
            if preferred_id in by_id:
                return by_id[preferred_id]

        for sec_func, param in tan_mechs.items():
            name_lower = (getattr(param, "name", "") or str(param)).lower()
            if any(
                token in name_lower
                for token in ("dkb app", "decoupled", "push", "app", "code")
            ):
                return sec_func

        return next(iter(tan_mechs))

    def _configure_tan_mechanism(self, client: Any) -> None:
        """Select pushTAN / DKB App before the dialog so init uses the right method."""
        try:
            if hasattr(client, "fetch_tan_mechanisms"):
                client.fetch_tan_mechanisms()

            tan_mechs = client.get_tan_mechanisms()
            if not tan_mechs:
                return

            for sec_func, param in tan_mechs.items():
                name = getattr(param, "name", "") or str(param)
                logger.info("Bank TAN mechanism available: %s -> %s", sec_func, name)

            push_mech_id = self._select_tan_mechanism(tan_mechs)
            logger.info("Selected TAN mechanism ID: %s", push_mech_id)
            client.set_tan_mechanism(push_mech_id)

            # DKB App (940) uses the primary registered device; do not set a TAN medium
            if str(push_mech_id) == "940":
                return

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

    def _submit_tan(self, client: Any, tan_response: Any, tan: str, is_decoupled: bool) -> Any:
        """Submit TAN; poll decoupled app approvals until confirmed or timeout."""
        from fints.client import NeedTANResponse

        use_decoupled = is_decoupled or not tan or tan.upper() == "OK"
        tan_value = "" if use_decoupled else tan

        result = client.send_tan(tan_response, tan_value)
        if not use_decoupled:
            return result

        for attempt in range(DECOUPLED_POLL_MAX_ATTEMPTS):
            if not isinstance(result, NeedTANResponse):
                logger.info("Decoupled app approval confirmed after %d poll(s)", attempt)
                return result
            time.sleep(DECOUPLED_POLL_INTERVAL_SECONDS)
            result = client.send_tan(result, "")

        raise TimeoutError(
            "App approval timed out after 2 minutes — approve the login in your banking app and try again."
        )

    def _complete_if_tan(self, client: Any, result: Any) -> Any:
        """If a FinTS call returned a decoupled TAN challenge, wait for app approval."""
        from fints.client import NeedTANResponse

        if isinstance(result, NeedTANResponse):
            return self._submit_tan(
                client, result, "", bool(getattr(result, "decoupled", False))
            )
        return result

    def _extract_balance_amount(self, balance: Any) -> Decimal | None:
        if balance is None:
            return None
        amount = getattr(balance, "amount", balance)
        try:
            if hasattr(amount, "amount"):
                return Decimal(str(amount.amount))
            return Decimal(str(amount))
        except Exception:
            logger.debug("Could not parse balance object: %r", balance)
            return None

    def _parse_transaction(self, stmt: Any, since: date) -> RawTransaction | None:
        """Normalize python-fints 5 MT940 objects, namedtuples, or CAMT dicts."""
        data = getattr(stmt, "data", stmt)

        def field(*names: str, default: Any = None) -> Any:
            for name in names:
                if isinstance(data, dict) and data.get(name) is not None:
                    return data[name]
                val = getattr(data, name, None)
                if val is not None:
                    return val
                val = getattr(stmt, name, None)
                if val is not None:
                    return val
            return default

        tx_date = field("date", "transaction_date", default=since)
        amount = field("amount")
        purpose = field("purpose", "description", default="") or ""
        applicant = field("applicant_name", "counterparty", "recipient_name", default="") or ""
        reference = field("bank_reference", "reference", default="") or ""
        value_date = field("entry_date", "value_date")

        if amount is None:
            return None
        amt = Decimal(str(amount.amount)) if hasattr(amount, "amount") else Decimal(str(amount))

        if hasattr(tx_date, "date") and not isinstance(tx_date, date):
            tx_date = tx_date.date()

        return RawTransaction(
            transaction_date=tx_date,
            value_date=value_date,
            amount=amt,
            description=purpose if isinstance(purpose, str) else str(purpose),
            counterparty=applicant if isinstance(applicant, str) else str(applicant),
            reference=reference if isinstance(reference, str) else str(reference),
        )

    def _parse_camt_bytes(self, xml_data: Any) -> list[dict[str, Any]]:
        """Parse CAMT.052/053 XML; DKB no longer returns MT940."""
        from lxml import etree

        if not xml_data:
            return []
        if isinstance(xml_data, str):
            xml_data = xml_data.encode("utf-8")

        try:
            from fints.camt_parser import camt053_to_dict

            return list(camt053_to_dict(xml_data) or [])
        except Exception as e:
            logger.info("Standard CAMT parser failed (%s); using generic Ntry parser", e)

        root = etree.fromstring(xml_data)
        for elem in root.getiterator():
            if hasattr(elem.tag, "find"):
                ind = elem.tag.find("}")
                if ind > 0:
                    elem.tag = elem.tag[ind + 1 :]

        parsed: list[dict[str, Any]] = []
        for ntry in root.xpath("//Ntry"):
            amt_el = ntry.find(".//Amt")
            if amt_el is None or not amt_el.text:
                continue
            amt = Decimal(amt_el.text)
            if (ntry.findtext(".//CdtDbtInd") or "DBIT") == "DBIT":
                amt = -amt
            book = ntry.findtext(".//BookgDt/Dt") or ntry.findtext(".//ValDt/Dt")
            val = ntry.findtext(".//ValDt/Dt") or book
            purpose = (
                ntry.findtext(".//RmtInf/Ustrd")
                or ntry.findtext(".//AddtlNtryInf")
                or ""
            )
            name = (
                ntry.findtext(".//RltdPties/Dbtr/Pty/Nm")
                or ntry.findtext(".//RltdPties/Cdtr/Pty/Nm")
                or ntry.findtext(".//RltdPties/Dbtr/Nm")
                or ntry.findtext(".//RltdPties/Cdtr/Nm")
                or ""
            )
            parsed.append(
                {
                    "date": date.fromisoformat(val) if val else None,
                    "entry_date": date.fromisoformat(book) if book else None,
                    "amount": amt,
                    "purpose": purpose,
                    "applicant_name": name,
                    "bank_reference": ntry.findtext(".//AcctSvcrRef") or "",
                }
            )
        return parsed

    def _transactions_from_xml(self, xml_result: Any) -> list[Any]:
        if not xml_result:
            return []
        if isinstance(xml_result, (tuple, list)) and len(xml_result) == 2:
            booked, pending = xml_result
        else:
            booked, pending = xml_result, []
        records: list[Any] = []
        for stream in list(booked or []) + list(pending or []):
            if not stream:
                continue
            try:
                records.extend(self._parse_camt_bytes(stream))
            except Exception as e:
                logger.warning("Failed to parse CAMT stream: %s", e)
        return records

    def _fetch_transactions_sync(self, client: Any, iban: str, since: date) -> list[RawTransaction]:
        from fints.client import NeedTANResponse

        sepa_accounts = self._complete_if_tan(client, client.get_sepa_accounts())
        if isinstance(sepa_accounts, NeedTANResponse):
            logger.error("TAN required to list accounts for transaction fetch")
            return []

        target_account = next(
            (acc for acc in sepa_accounts if getattr(acc, "iban", "") == iban),
            None,
        )
        if target_account is None:
            logger.warning("Account with IBAN %s not found", iban)
            return []

        end = date.today()
        raw = self._complete_if_tan(
            client, client.get_transactions(target_account, since, end, True)
        )
        if isinstance(raw, NeedTANResponse):
            logger.error("TAN required to fetch transactions for IBAN %s", iban)
            return []

        raw_items = list(raw or [])
        logger.info(
            "get_transactions returned %d %s item(s) for %s",
            len(raw_items),
            type(raw).__name__,
            iban[-4:] if iban else "?",
        )

        parsed: list[RawTransaction] = []
        for stmt in raw_items:
            item = self._parse_transaction(stmt, since)
            if item is not None:
                parsed.append(item)

        if not parsed:
            logger.info("MT940 empty or unparsed — trying CAMT/XML for %s", iban)
            xml_result = self._complete_if_tan(
                client, client.get_transactions_xml(target_account, since, end)
            )
            if isinstance(xml_result, NeedTANResponse):
                logger.error("TAN required for CAMT fetch on %s", iban)
                return []
            for rec in self._transactions_from_xml(xml_result):
                item = self._parse_transaction(rec, since)
                if item is not None:
                    parsed.append(item)

        logger.info("Fetched %d transactions for IBAN %s since %s", len(parsed), iban, since)
        return parsed

    async def connect(
        self, bank_blz: str, fints_url: str, login_name: str, pin: str
    ) -> AuthResult:
        """Establish a FinTS connection, check if TAN is needed."""
        try:
            client = await asyncio.to_thread(
                self._create_client, bank_blz, fints_url, login_name, pin
            )

            # TAN method must be selected before the dialog, otherwise DKB
            # issues the init challenge with the wrong (often chipTAN) mechanism.
            await asyncio.to_thread(self._configure_tan_mechanism, client)
            await asyncio.to_thread(client.__enter__)

            if client.init_tan_response:
                tan_response = client.init_tan_response
                is_decoupled = bool(getattr(tan_response, "decoupled", False))
                challenge_msg = getattr(
                    tan_response,
                    "challenge",
                    "Please approve login in your DKB Banking App",
                )
                tan_type = "pushTAN / App Approval" if is_decoupled else "TAN"
                return AuthResult(
                    success=True,
                    requires_tan=True,
                    tan_challenge=challenge_msg,
                    tan_type=tan_type,
                    session_data={
                        "client": client,
                        "tan_response": tan_response,
                        "decoupled": is_decoupled,
                    },
                )

            return AuthResult(
                success=True,
                requires_tan=False,
                session_data={"client": client},
            )

        except Exception as e:
            cause = e.__cause__ or e.__context__
            detail = str(e)
            if cause and str(cause) != detail:
                detail = f"{e} ({cause})"
            if "400" in detail or "system_id" in detail.lower():
                detail = (
                    "DKB rejected the FinTS handshake (HTTP 400 / missing system_id). "
                    "This usually means the FinTS product ID is unknown to DKB. "
                    "Set FINTS_PRODUCT_ID in .env — register at "
                    "https://www.fints.org/de/hersteller/produktregistrierung"
                )
            logger.error("FinTS connection failed: %s", detail, exc_info=True)
            return AuthResult(success=False, error=detail)

    async def handle_tan(self, session_data: Any, tan: str) -> AuthResult:
        """Submit TAN or poll for decoupled app approval."""
        try:
            client = session_data["client"]
            tan_response = session_data.get("tan_response")
            is_decoupled = session_data.get("decoupled", False)

            if tan_response:
                await asyncio.to_thread(
                    self._submit_tan, client, tan_response, tan, is_decoupled
                )

            return AuthResult(
                success=True,
                requires_tan=False,
                session_data=session_data,
            )
        except Exception as e:
            logger.error("TAN verification failed: %s", e)
            return AuthResult(success=False, error=str(e))

    def _fetch_accounts_sync(self, client: Any) -> list[BankAccountInfo]:
        from fints.client import NeedTANResponse

        sepa_accounts = self._complete_if_tan(client, client.get_sepa_accounts())
        if isinstance(sepa_accounts, NeedTANResponse):
            logger.error("TAN required to fetch accounts")
            return []

        accounts = []
        for acc in sepa_accounts:
            iban = getattr(acc, "iban", "") or ""
            currency = getattr(acc, "currency", "EUR") or "EUR"
            live_balance = None
            try:
                raw_balance = self._complete_if_tan(client, client.get_balance(acc))
                live_balance = self._extract_balance_amount(raw_balance)
                logger.info(
                    "Balance for %s: %s %s",
                    iban[-4:] if iban else "?",
                    live_balance,
                    currency,
                )
            except Exception as be:
                logger.warning("Could not fetch balance for %s: %s", iban, be)

            accounts.append(
                BankAccountInfo(
                    iban=iban,
                    account_name=getattr(acc, "accountnumber", "Account"),
                    currency=currency,
                    balance=live_balance,
                )
            )
        return accounts

    async def fetch_accounts(self, session_data: Any) -> list[BankAccountInfo]:
        """Fetch SEPA accounts and current balances from the bank."""
        try:
            client = session_data["client"]
            return await asyncio.to_thread(self._fetch_accounts_sync, client)
        except Exception as e:
            logger.error("Failed to fetch accounts: %s", e)
            return []

    async def fetch_transactions(
        self, session_data: Any, iban: str, since: date
    ) -> list[RawTransaction]:
        """Fetch transactions from a specific account since a given date."""
        try:
            client = session_data["client"]
            return await asyncio.to_thread(
                self._fetch_transactions_sync, client, iban, since
            )
        except Exception as e:
            logger.error("Failed to fetch transactions: %s", e, exc_info=True)
            return []

    async def disconnect(self, session_data: Any) -> None:
        """Close the FinTS dialog."""
        try:
            client = session_data.get("client")
            if client:
                await asyncio.to_thread(client.__exit__, None, None, None)
        except Exception as e:
            logger.warning("Error disconnecting FinTS client: %s", e)
