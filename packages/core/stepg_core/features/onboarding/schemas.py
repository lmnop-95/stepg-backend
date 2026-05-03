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
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from stepg_core.core.biz_reg_no import normalize_to_digits
from stepg_core.features.companies.models import CERTIFICATIONS, CORPORATE_TYPES


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


class OnboardingCompleteRequest(BaseModel):
    """`POST /onboarding/complete` 입력 — 사용자 검수 후 최종 확정값.

    Q50 단일 schema: `Company` 컬럼과 1:1 mirror + KSIC 매핑 input
    (`business_types`, service 단 `lookup_first_ksic_code` 입력) +
    `fields_of_work_ids` (commit 8 `Project` M2M 적재 input, commit 7 에서는
    Pydantic validate 만).

    OCR confirmed 중 `corp_name`/`representative_name`/`address` 등은 Phase 1
    `Company` 미저장 (pitfalls D — preview only). 본 schema 도 받지 않음.
    저장 컬럼만 input contract 에 포함.
    """

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    # Q47 — dash 포함 입력 수용 + validator 가 10자리 raw strip
    biz_reg_no: str

    # Q4 pass5: `min_length=1` 제거. `_check_corporate_type` 의 `CORPORATE_TYPES`
    # membership 검증이 빈 문자열을 이미 거부하므로 Field-level guard 와 중복.
    corporate_type: str
    employee_count: int | None = Field(default=None, ge=0)
    revenue_last_year: int | None = Field(default=None, ge=0)
    sido: Annotated[str, Field(min_length=1)]
    established_on: date | None = None

    # KSIC 매핑 input — service 가 `lookup_first_ksic_code` 호출, Company
    # 컬럼에는 결과 코드 (`industry_ksic_code`) 만 저장. `business_types`
    # 자체는 미저장.
    business_types: tuple[str, ...] = ()

    # 인증 6종 (선택, `CERTIFICATIONS` 부분집합)
    certifications: tuple[str, ...] = ()

    # Q46 — UUID list, 정확히 3개. commit 8 가 Project M2M 에 적재.
    fields_of_work_ids: tuple[UUID, UUID, UUID]

    @field_validator("biz_reg_no")
    @classmethod
    def _strip_biz_reg_no(cls, v: str) -> str:
        digits = normalize_to_digits(v)
        if digits is None:
            raise ValueError("biz_reg_no는 10자리 숫자여야 합니다")
        return digits

    @field_validator("corporate_type")
    @classmethod
    def _check_corporate_type(cls, v: str) -> str:
        if v not in CORPORATE_TYPES:
            raise ValueError(f"corporate_type은 {CORPORATE_TYPES} 중 하나여야 합니다")
        return v

    @field_validator("certifications")
    @classmethod
    def _check_certifications(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        invalid = set(v) - set(CERTIFICATIONS)
        if invalid:
            raise ValueError(
                f"인증 항목은 {CERTIFICATIONS} 중에서만 선택 가능합니다 (잘못된 값: {sorted(invalid)})"
            )
        return v

    @field_validator("fields_of_work_ids")
    @classmethod
    def _unique_fields_of_work(cls, v: tuple[UUID, UUID, UUID]) -> tuple[UUID, UUID, UUID]:
        if len(set(v)) != len(v):
            raise ValueError("fields_of_work_ids는 서로 다른 3개여야 합니다")
        return v


class OnboardingCompleteResponse(BaseModel):
    """`POST /onboarding/complete` 응답 — Company + default Project 식별자.

    commit 7 = `company_id` 만, commit 8 = `project_id` 추가 (단일 atomic tx).
    M6 매칭 엔진 (`/recommendations`) 이 default Project 를 활용 시 client 가
    follow-up GET 없이 바로 사용.
    """

    model_config = ConfigDict(frozen=True)
    company_id: int
    project_id: int


__all__ = ["OcrBizRegResponse", "OnboardingCompleteRequest", "OnboardingCompleteResponse"]
