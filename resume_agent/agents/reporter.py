from __future__ import annotations

from typing import List, Optional

from resume_agent.models import Confidence, DagResult, Decision, ReportModel


def build_report(*, dag_result: DagResult) -> ReportModel:
    """
    Reporter Agent：输出严格 JSON Schema（通过 ReportModel 保证字段正确）。
    """
    decision: Decision = dag_result.preliminary_decision
    matched_path: Optional[str] = dag_result.matched_path
    confidence: Confidence = dag_result.confidence
    reason: str = dag_result.reason or ""
    warnings: List[str] = dag_result.warnings or []

    # 最终再做一次“保守兜底”：任何关键不确定都不允许强行 Y/N
    if decision in (Decision.Y, Decision.N) and warnings:
        # 若警告包含“严格模式下教育时间不完整/无法确认”等，倾向信息不足
        if any(k in w for w in warnings for k in ["无法确认", "不完整", "未识别到教育起止时间"]):
            decision = Decision.INSUFFICIENT
            matched_path = None
            confidence = Confidence.low
            reason = reason or "存在关键字段不确定，按规则输出信息不足"

    return ReportModel(
        decision=decision,
        matched_path=matched_path,
        confidence=confidence,
        reason=reason,
        warnings=warnings,
    )

