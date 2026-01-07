from __future__ import annotations

from typing import List, Optional, Tuple

from resume_agent.models import (
    CertificateRequirement,
    Decision,
    EducationLevel,
    ExtractedCertificates,
    ExtractedEducation,
    PathEvaluation,
    PathSpec,
)


_LEVEL_ORDER = {
    EducationLevel.unknown: 0,
    EducationLevel.associate: 1,
    EducationLevel.bachelor: 2,
    EducationLevel.master: 3,
    EducationLevel.phd: 4,
}


def _education_meets_min(extracted: EducationLevel, required: EducationLevel) -> Optional[bool]:
    # 返回 True/False/None（未知）
    if required == EducationLevel.unknown:
        return True
    if extracted == EducationLevel.unknown:
        return None
    return _LEVEL_ORDER[extracted] >= _LEVEL_ORDER[required]


def _full_time_ok(extracted: Optional[bool], required: bool) -> Optional[bool]:
    if not required:
        return True
    if extracted is None:
        return None
    return extracted is True


def _date_ok(extracted: ExtractedEducation, date_strict: bool) -> Optional[bool]:
    if not date_strict:
        return True
    if extracted.start and extracted.end:
        return True
    return None


def _certs_ok(
    extracted: ExtractedCertificates, requirements: List[CertificateRequirement]
) -> Tuple[Optional[bool], List[str]]:
    # 返回 (ok, missing_reason)
    reasons: List[str] = []
    for req in requirements:
        if req.name not in extracted.matched:
            reasons.append(f"缺少证书：{req.name}")
    if not requirements:
        return True, reasons
    if reasons:
        # 无法区分 fail vs unknown：由抽取器/警告决定，这里默认 unknown（更保守）
        return None, reasons
    return True, reasons


def evaluate_path(
    *,
    path: PathSpec,
    extracted_education: ExtractedEducation,
    extracted_certs: ExtractedCertificates,
) -> PathEvaluation:
    reasons: List[str] = []
    warnings: List[str] = []

    # 教育：最低学历
    edu_min = _education_meets_min(extracted_education.level, path.education.min_level)
    if edu_min is False:
        return PathEvaluation(
            path_name=path.name,
            status="fail",
            reasons=[f"学历不满足最低要求：需要 >= {path.education.min_level}"],
            warnings=[],
        )
    if edu_min is None:
        reasons.append(f"学历未知，无法确认是否满足 >= {path.education.min_level}")

    # 教育：全日制
    ft = _full_time_ok(extracted_education.full_time, path.education.full_time_required)
    if ft is False:
        return PathEvaluation(
            path_name=path.name,
            status="fail",
            reasons=["不满足全日制要求"],
            warnings=[],
        )
    if ft is None and path.education.full_time_required:
        reasons.append("全日制信息缺失，无法确认")

    # 教育：时间完整性（严格模式下要求可解析）
    dt = _date_ok(extracted_education, path.education.date_strict)
    if dt is None and path.education.date_strict:
        reasons.append("教育起止时间不完整/不可解析（严格模式）")

    # 证书
    cert_ok, cert_missing = _certs_ok(extracted_certs, path.certificates)
    if cert_ok is None:
        reasons.extend(cert_missing)

    warnings.extend(extracted_education.warnings)
    warnings.extend(extracted_certs.warnings)

    # 综合判定：只要有任何 unknown 原因，就 unknown；否则 pass
    unknown_reasons = [r for r in reasons if "未知" in r or "缺失" in r or "不完整" in r or "无法确认" in r or "缺少证书" in r]
    if unknown_reasons:
        return PathEvaluation(path_name=path.name, status="unknown", reasons=reasons, warnings=warnings)

    return PathEvaluation(path_name=path.name, status="pass", reasons=["满足该路径全部要求"], warnings=warnings)


def choose_final_decision(evals: List[PathEvaluation]) -> Tuple[Decision, Optional[str]]:
    # 任何 pass => Y；否则如果存在 unknown => 信息不足；否则 N
    for e in evals:
        if e.status == "pass":
            return Decision.Y, e.path_name
    for e in evals:
        if e.status == "unknown":
            return Decision.INSUFFICIENT, None
    return Decision.N, None

