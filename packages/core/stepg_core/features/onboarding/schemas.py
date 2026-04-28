"""Onboarding boundary DTOs (M5-api).

`OcrBizRegResponse` is the BE-side contract returned by `recognize_bizlicense`
and forwarded to the FE by `POST /onboarding/ocr` (commit 3). The raw CLOVA
response shape is parsed via the `*Raw` Pydantic models below; mapping to
`OcrBizRegResponse` lives in `sources/clova_bizlicense.py` (Q25).

Recon notes: `docs/.local/feat/onboarding/M5-api/clova-ocr-recon.md`.

Legacy (`docs/legacy/pitfalls.md` §M5):
- L4: BE owns parsing — never passthrough raw CLOVA shape to FE.
- D: business registration number stored as 10-digit raw (dash strip).
- D: `established_on` is `DATE`; M1 schema gap closed by 0013 migration.
- PIPA: `socialNumber`/`coRepSocialNum` raw keys exist but are never declared
  in `BizLicenseResultRaw` — `extra="ignore"` silently drops them so they
  cannot accidentally surface in logs or persist (Q20).
- Q14: `confidenceScore` from CLOVA is constantly 0.0 — DTO drops the field.
- Q24: `boundingPolys` dropped (UI overlay is Phase 1.5).
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class BizLicenseElementRaw(BaseModel):
    """Single OCR cell — text only.

    `confidenceScore` / `boundingPolys` / `maskingPolys` / `keyText` /
    `formatted` are dropped at the schema boundary (Q14/Q24/Q21).
    `extra="ignore"` lets future CLOVA fields arrive without breaking the
    parse.
    """

    model_config = ConfigDict(extra="ignore")
    text: str = ""


class BizLicenseResultRaw(BaseModel):
    """`bizLicense.result` — 15 known keys (Q19).

    Documented CLOVA keys `socialNumber` and `coRepSocialNum` are intentionally
    omitted here (Q20 PIPA). With `extra="ignore"`, any future incidental
    arrival of those keys is silently dropped at parse time and never reaches
    the mapping function.
    """

    model_config = ConfigDict(extra="ignore")

    bisAddress: tuple[BizLicenseElementRaw, ...] = ()
    bisArea: tuple[BizLicenseElementRaw, ...] = ()
    bisItem: tuple[BizLicenseElementRaw, ...] = ()
    bisType: tuple[BizLicenseElementRaw, ...] = ()
    companyName: tuple[BizLicenseElementRaw, ...] = ()
    corpName: tuple[BizLicenseElementRaw, ...] = ()
    corpRegisterNum: tuple[BizLicenseElementRaw, ...] = ()
    documentType: tuple[BizLicenseElementRaw, ...] = ()
    headAddress: tuple[BizLicenseElementRaw, ...] = ()
    issuanceDate: tuple[BizLicenseElementRaw, ...] = ()
    issuanceReason: tuple[BizLicenseElementRaw, ...] = ()
    openDate: tuple[BizLicenseElementRaw, ...] = ()
    registerNumber: tuple[BizLicenseElementRaw, ...] = ()
    repName: tuple[BizLicenseElementRaw, ...] = ()
    taxType: tuple[BizLicenseElementRaw, ...] = ()


class BizLicenseRaw(BaseModel):
    model_config = ConfigDict(extra="ignore")
    result: BizLicenseResultRaw


class BizLicenseImageRaw(BaseModel):
    model_config = ConfigDict(extra="ignore")
    inferResult: Literal["SUCCESS", "FAILURE", "ERROR"]
    message: str = ""
    bizLicense: BizLicenseRaw | None = None


class BizLicenseResponseRaw(BaseModel):
    """Top-level CLOVA Document OCR bizLicense response."""

    model_config = ConfigDict(extra="ignore")
    images: tuple[BizLicenseImageRaw, ...] = Field(min_length=1)


class OcrBizRegResponse(BaseModel):
    """Frozen boundary DTO returned by `recognize_bizlicense`.

    Field cardinality (Q15) — multi where domain semantics require it
    (공동대표 / multi-business), single elsewhere. `business_address` and
    `head_address` are both retained (Q16); the choice of which feeds
    `Company.address` is deferred to commit 5 (`POST /onboarding/complete`).
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    corp_name: str | None = None
    company_name: str | None = None
    representative_names: tuple[str, ...] = ()
    biz_reg_no: str | None = None
    corp_reg_no: str | None = None
    business_address: str | None = None
    head_address: str | None = None
    business_types: tuple[str, ...] = ()
    business_items: tuple[str, ...] = ()
    business_area: str | None = None
    established_on: date | None = None
    issuance_date: date | None = None
    tax_type: str | None = None
    document_type: str | None = None


__all__ = ["OcrBizRegResponse"]
