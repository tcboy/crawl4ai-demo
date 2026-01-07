from __future__ import annotations

import re
from typing import List

from resume_agent.models import CertificateRequirement, ExtractedCertificates


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def extract_certificates(
    *, resume_text: str, requirements: List[CertificateRequirement], lenient_mode: bool
) -> ExtractedCertificates:
    """
    证书抽取是确定性的：基于关键词/模式匹配，不调用LLM。
    lenient_mode=True 时允许更宽松的证据（并给出 warnings）。
    """
    text = resume_text or ""
    compact = _normalize(text)

    matched: List[str] = []
    raw_evidence: dict[str, List[str]] = {}
    warnings: List[str] = []

    for req in requirements:
        evidences: List[str] = []
        name = req.name
        # 证书名称出现
        if _normalize(name) and _normalize(name) in compact:
            evidences.append(f"出现证书名称：{name}")

        # 必备关键词（例如 科目一/二）
        missing_keywords = []
        for kw in req.must_have_keywords:
            if _normalize(kw) in compact:
                evidences.append(f"出现关键词：{kw}")
            else:
                missing_keywords.append(kw)

        # 宽松：允许“通过xx考试/持有xx资格/已取得xx证”等泛化表述
        generic_ok = False
        if lenient_mode and req.allow_generic_pass:
            patterns = [
                rf"通过.*{re.escape(name)}",
                rf"已通过.*{re.escape(name)}",
                rf"持有.*{re.escape(name)}",
                rf"取得.*{re.escape(name)}",
                rf"{re.escape(name)}.*通过",
            ]
            for p in patterns:
                if re.search(p, text):
                    generic_ok = True
                    evidences.append(f"宽松证据匹配：{p}")
                    break

        # 判定该证书是否“满足”
        satisfied = False
        if req.must_have_keywords:
            # 必须全部关键词都存在；宽松模式下允许 generic_ok 兜底
            if not missing_keywords:
                satisfied = True
            elif generic_ok:
                satisfied = True
                warnings.append(
                    f"证书 {name} 未明确包含 {missing_keywords}，但在宽松模式下按泛化表述通过（降低置信度）"
                )
        else:
            # 只有名称即可
            if evidences:
                satisfied = True
            elif generic_ok:
                satisfied = True

        if satisfied:
            matched.append(name)
        if evidences:
            raw_evidence[name] = evidences

    return ExtractedCertificates(matched=matched, raw_evidence=raw_evidence, warnings=warnings)

