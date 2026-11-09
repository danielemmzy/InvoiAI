from __future__ import annotations

import asyncio
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable

import httpx

from app.repositories.fx.rate_repository import FXRateRepository
from app.core.error_handler import PlatformError


FRANKFURTER_BASE_URL = "https://api.frankfurter.dev/v2"


class FXRateUnavailable(PlatformError):
    def __init__(self, message: str):
        super().__init__(
            message,
            code="FX_PROVIDER_UNAVAILABLE",
            status_code=503,
            retryable=True,
            service="fx_provider",
        )


class FXService:
    """Historical daily FX rates with database caching.

    Invoice amounts and currencies remain untouched. Reporting conversion is
    performed only at read time using the invoice date (or the most recent
    published rate on/before that date).
    """

    def __init__(self, repository: FXRateRepository | None = None):
        self.repository = repository or FXRateRepository()

    @staticmethod
    def _provider_query(base: str, quote: str) -> dict[str, str]:
        # CBN is especially useful for NGN reference rates. For other pairs,
        # Frankfurter's blended provider set is used.
        if "NGN" in {base, quote}:
            return {"providers": "CBN"}
        return {}

    async def _fetch_range(
        self,
        base: str,
        quote: str,
        date_from: date,
        date_to: date,
    ) -> list[dict]:
        params = {
            "from": date_from.isoformat(),
            "to": date_to.isoformat(),
            "base": base,
            "quotes": quote,
            **self._provider_query(base, quote),
        }
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.get(f"{FRANKFURTER_BASE_URL}/rates", params=params)
            response.raise_for_status()
            payload = response.json()

        if not isinstance(payload, list):
            raise FXRateUnavailable(f"Unexpected FX provider response for {base}/{quote}")

        rows: list[dict] = []
        for item in payload:
            if item.get("base") != base or item.get("quote") != quote:
                continue
            if item.get("rate") is None or item.get("date") is None:
                continue
            rows.append(
                {
                    "base_currency": base,
                    "quote_currency": quote,
                    "rate": str(Decimal(str(item["rate"]))),
                    "rate_date": item["date"],
                    "source": "frankfurter:CBN" if "NGN" in {base, quote} else "frankfurter:blended",
                    "is_forward_filled": False,
                }
            )
        return rows

    async def ensure_rates(
        self,
        base_currencies: Iterable[str],
        quote_currency: str,
        date_from: date,
        date_to: date,
    ) -> dict[tuple[str, str], Decimal]:
        quote = quote_currency.upper()
        bases = sorted({str(c).upper() for c in base_currencies if c and str(c).upper() != quote})
        if not bases:
            return {}

        results: dict[tuple[str, str], Decimal] = {}

        async def ensure(base: str) -> tuple[str, list[dict]]:
            cached = self.repository.get_rates(
                base_currency=base,
                quote_currency=quote,
                date_from=date_from,
                date_to=date_to,
            )
            cached_dates = [date.fromisoformat(str(row["rate_date"])[:10]) for row in cached]
            if cached_dates and min(cached_dates) <= date_from and max(cached_dates) >= date_to:
                return base, cached

            try:
                fetched = await self._fetch_range(base, quote, date_from, date_to)
            except Exception as exc:
                raise FXRateUnavailable(
                    f"Unable to load FX rates for {base}/{quote}."
                ) from exc
            self.repository.upsert_rates(fetched)
            return base, fetched

        pairs = await asyncio.gather(*(ensure(base) for base in bases))

        for base, rows in pairs:
            by_date = {
                date.fromisoformat(str(row["rate_date"])[:10]): Decimal(str(row["rate"]))
                for row in rows
            }
            current = date_from
            last_rate: Decimal | None = None
            while current <= date_to:
                if current in by_date:
                    last_rate = by_date[current]
                if last_rate is not None:
                    results[(base, current.isoformat())] = last_rate
                current += timedelta(days=1)

        return results

    async def convert_rows(
        self,
        rows: list[dict],
        reporting_currency: str,
        *,
        date_from: date,
        date_to: date,
    ) -> list[dict]:
        quote = reporting_currency.upper()
        if not rows:
            return rows

        sources = {str(row.get("currency") or quote).upper() for row in rows}
        rates = await self.ensure_rates(sources, quote, date_from, date_to)

        converted: list[dict] = []
        for row in rows:
            item = dict(row)
            source = str(row.get("currency") or quote).upper()
            amount = Decimal(str(row.get("total_amount") or 0))
            paid = Decimal(str(row.get("amount_paid") or 0))
            balance = Decimal(str(row.get("amount_due") or 0))

            if source == quote:
                rate = Decimal("1")
                rate_date = str(row.get("document_date") or date_to)[:10]
            else:
                raw_date = row.get("document_date") or row.get("created_at") or date_to
                effective_date = date.fromisoformat(str(raw_date)[:10])
                rate = rates.get((source, effective_date.isoformat()))
                if rate is None:
                    raise FXRateUnavailable(
                        f"No FX rate available for {source}/{quote} on {effective_date.isoformat()}."
                    )
                rate_date = effective_date.isoformat()

            item["reporting_currency"] = quote
            item["fx_rate"] = rate
            item["fx_rate_date"] = rate_date
            item["reporting_total_amount"] = amount * rate
            item["reporting_paid_amount"] = paid * rate
            item["reporting_balance_due"] = balance * rate
            converted.append(item)

        return converted
