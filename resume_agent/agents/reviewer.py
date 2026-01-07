from __future__ import annotations

import re
from typing import List, Tuple

from resume_agent.models import DagResult, Decision, JobModel, ReflectionItem


def _has_year_range_only_warning(dag: DagResult) -> bool:
    return any("仅为年份区间" in w or "未识别到教育起止时间" in w for w in dag.warnings)


def _has_certificate_keyword_uncertainty(dag: DagResult) -> bool:
    return any("未明确包含" in w for w in dag.warnings)

def _has_missing_certificate_reason(dag: DagResult) -> bool:
    return any(
        "缺少证书" in r
        for e in dag.path_evaluations
        for r in (e.reasons or [])
    )


def review_decision(
    *,
    jd_text: str,
    resume_text: str,
    job_model: JobModel,
    dag_result: DagResult,
) -> Tuple[List[ReflectionItem], bool, dict]:
    """
    Reviewer Agent：基于规则做反思（不能“凭感觉”）。

    返回：
    - reflection_items: 发现的问题/建议
    - need_retry: 是否触发修正循环
    - directives: 给 Planner/Executor 的确定性指令开关
    """
    items: List[ReflectionItem] = []
    directives = {
        "executor_lenient_mode": False,
        "planner_relax_date_rules": False,
        "planner_enable_fuzzy": False,
    }

    # 1) 关键字段缺失检查（教育时间、全日制、证书科目明细等）
    if dag_result.preliminary_decision == Decision.INSUFFICIENT:
        # 若不确定主要来自教育时间格式，可建议放宽
        if job_model.global_date_strict and _has_year_range_only_warning(dag_result):
            items.append(
                ReflectionItem(
                    issue="教育时间格式不标准导致无法确认全日制/时间完整性",
                    suggestion="放宽教育时间严格要求，并允许根据学制年限推断全日制",
                    severity="high",
                )
            )
            directives["planner_relax_date_rules"] = True
            directives["executor_lenient_mode"] = True

        # 若不确定来自证书缺少科目明细，但出现“通过xx考试”
        if _has_certificate_keyword_uncertainty(dag_result):
            # 仅当简历里出现典型泛化表述时才建议启用
            if re.search(r"通过.*基金从业资格|基金从业资格.*通过|通过基金从业资格考试", resume_text):
                items.append(
                    ReflectionItem(
                        issue="证书科目明细缺失，但存在‘通过基金从业资格考试’等泛化表述",
                        suggestion="启用证书宽松匹配（允许泛化表述满足），并降低置信度",
                        severity="medium",
                    )
                )
                directives["planner_enable_fuzzy"] = True
                directives["executor_lenient_mode"] = True

        # 若不确定来自“缺少证书”，但简历出现“通过xx考试”等泛化表述（可能只是命名不一致/缺少科目明细）
        if _has_missing_certificate_reason(dag_result):
            if re.search(r"通过.*基金从业|基金从业.*通过|通过基金从业资格考试|通过基金从业资格", resume_text):
                items.append(
                    ReflectionItem(
                        issue="评估认为缺少证书，但简历存在‘通过基金从业…’等证据，可能需宽松证书匹配",
                        suggestion="启用证书宽松匹配（允许泛化表述/名称近似），并重跑 Executor",
                        severity="high",
                    )
                )
                directives["planner_enable_fuzzy"] = True
                directives["executor_lenient_mode"] = True

    # 2) 逻辑冲突检查（示例：要求全日制本科，但简历只有“2020年本科”无起止）
    if any(p.education.full_time_required for p in job_model.paths):
        if dag_result.extracted_education.full_time is None and "全日制信息缺失" in " ".join(
            r for e in dag_result.path_evaluations for r in e.reasons
        ):
            items.append(
                ReflectionItem(
                    issue="JD要求全日制，但简历未明确全日制属性",
                    suggestion="若出现合理学制年限（如2019-2022），可在宽松模式下推断；否则保持信息不足",
                    severity="medium",
                )
            )

    # 3) 是否“过于激进”：如果给 N，但存在明显可放宽点，应先信息不足/重试
    if dag_result.preliminary_decision == Decision.N:
        if job_model.global_date_strict and _has_year_range_only_warning(dag_result):
            items.append(
                ReflectionItem(
                    issue="初步判定为 N，但教育时间解析失败可能导致误杀",
                    suggestion="先放宽教育时间规则重跑；若仍失败再判 N",
                    severity="high",
                )
            )
            directives["planner_relax_date_rules"] = True
            directives["executor_lenient_mode"] = True

        if _has_certificate_keyword_uncertainty(dag_result):
            items.append(
                ReflectionItem(
                    issue="初步判定为 N，但证书证据可能仅是表述不规范",
                    suggestion="启用证书宽松匹配重跑；若仍无法满足再判 N",
                    severity="medium",
                )
            )
            directives["planner_enable_fuzzy"] = True
            directives["executor_lenient_mode"] = True

    need_retry = any(
        directives[k] for k in ["executor_lenient_mode", "planner_relax_date_rules", "planner_enable_fuzzy"]
    )
    return items, need_retry, directives

