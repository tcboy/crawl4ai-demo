from __future__ import annotations

from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, StateGraph

from resume_agent.evaluator import choose_final_decision, evaluate_path
from resume_agent.extractors.certificates import extract_certificates
from resume_agent.extractors.education import extract_education
from resume_agent.models import (
    Confidence,
    DagResult,
    Decision,
    ExtractedCertificates,
    ExtractedEducation,
    JobModel,
    PathEvaluation,
)


class _DagState(TypedDict, total=False):
    resume_text: str
    job_model: Dict[str, Any]
    lenient_mode: bool

    extracted_education: Dict[str, Any]
    extracted_certificates: Dict[str, Any]
    path_evaluations: List[Dict[str, Any]]
    preliminary_decision: str
    matched_path: str | None
    confidence: str
    reason: str
    warnings: List[str]


def _node_extract_education(state: _DagState) -> Dict[str, Any]:
    jm = JobModel.model_validate(state["job_model"])
    # education 以“最严格”的路径为准：只要任一条要求 strict，就 strict（除非全局放宽）
    date_strict = jm.global_date_strict and any(p.education.date_strict for p in jm.paths)
    allow_infer_full_time = state.get("lenient_mode", False) and any(
        p.education.allow_infer_full_time for p in jm.paths
    )
    edu = extract_education(
        resume_text=state["resume_text"],
        date_strict=date_strict,
        allow_infer_full_time=allow_infer_full_time,
    )
    return {"extracted_education": edu.model_dump()}


def _node_extract_certificates(state: _DagState) -> Dict[str, Any]:
    jm = JobModel.model_validate(state["job_model"])
    reqs = []
    for p in jm.paths:
        reqs.extend(p.certificates)
    certs = extract_certificates(
        resume_text=state["resume_text"],
        requirements=reqs,
        lenient_mode=state.get("lenient_mode", False) or jm.global_allow_fuzzy,
    )
    return {"extracted_certificates": certs.model_dump()}


def _node_evaluate_paths(state: _DagState) -> Dict[str, Any]:
    jm = JobModel.model_validate(state["job_model"])
    edu = ExtractedEducation.model_validate(state.get("extracted_education") or {})
    certs = ExtractedCertificates.model_validate(state.get("extracted_certificates") or {})

    evals: List[PathEvaluation] = []
    for p in jm.paths:
        evals.append(evaluate_path(path=p, extracted_education=edu, extracted_certs=certs))

    decision, matched = choose_final_decision(evals)

    # 置信度规则（确定性）
    warnings: List[str] = []
    for e in evals:
        warnings.extend(e.warnings)
    # 去重
    warnings = list(dict.fromkeys([w for w in warnings if w]))

    if decision == Decision.Y:
        confidence = Confidence.high if not warnings else Confidence.medium
        reason = _build_reason_for_yes(evals, matched, edu, certs)
    elif decision == Decision.INSUFFICIENT:
        confidence = Confidence.low
        reason = _build_reason_for_insufficient(evals)
    else:
        confidence = Confidence.medium if not warnings else Confidence.low
        reason = _build_reason_for_no(evals)

    return {
        "path_evaluations": [e.model_dump() for e in evals],
        "preliminary_decision": decision.value,
        "matched_path": matched,
        "confidence": confidence.value,
        "reason": reason,
        "warnings": warnings,
    }


def _build_reason_for_yes(
    evals: List[PathEvaluation],
    matched_path: str | None,
    edu: ExtractedEducation,
    certs: ExtractedCertificates,
) -> str:
    mp = matched_path or "某路径"
    pieces = [f"满足路径：{mp}"]
    if edu.level.value != "unknown":
        edu_part = f"学历={edu.level.value}"
        if edu.start and edu.end:
            edu_part += f"（{edu.start}–{edu.end}）"
        pieces.append(edu_part)
    if certs.matched:
        pieces.append("证书=" + ",".join(certs.matched))
    return "；".join(pieces)


def _build_reason_for_insufficient(evals: List[PathEvaluation]) -> str:
    unknowns = [e for e in evals if e.status == "unknown"]
    if not unknowns:
        return "存在关键字段不确定，无法给出可靠结论"
    # 取一条代表性原因
    e0 = unknowns[0]
    return f"路径 {e0.path_name} 需要更多信息：{';'.join(e0.reasons[:3])}"


def _build_reason_for_no(evals: List[PathEvaluation]) -> str:
    fails = [e for e in evals if e.status == "fail"]
    if not fails:
        return "所有路径均不满足"
    e0 = fails[0]
    return f"路径 {e0.path_name} 不满足：{';'.join(e0.reasons[:3])}"


def build_and_run_dag(*, job_model: JobModel, resume_text: str, lenient_mode: bool) -> DagResult:
    """
    Executor Agent：根据 JobModel 动态构建 LangGraph DAG 并执行，输出初步决策。
    注意：该 DAG 的所有节点均为确定性规则。
    """
    graph = StateGraph(_DagState)
    graph.add_node("extract_education", _node_extract_education)
    graph.add_node("extract_certificates", _node_extract_certificates)
    graph.add_node("evaluate_paths", _node_evaluate_paths)

    graph.set_entry_point("extract_education")
    graph.add_edge("extract_education", "extract_certificates")
    graph.add_edge("extract_certificates", "evaluate_paths")
    graph.add_edge("evaluate_paths", END)

    app = graph.compile()
    out = app.invoke(
        {
            "resume_text": resume_text,
            "job_model": job_model.model_dump(),
            "lenient_mode": bool(lenient_mode),
        }
    )

    # 组装 DagResult（可回溯）
    dr = DagResult(
        lenient_mode=bool(lenient_mode),
        extracted_education=ExtractedEducation.model_validate(out.get("extracted_education") or {}),
        extracted_certificates=ExtractedCertificates.model_validate(out.get("extracted_certificates") or {}),
        path_evaluations=[PathEvaluation.model_validate(x) for x in (out.get("path_evaluations") or [])],
        preliminary_decision=Decision(out.get("preliminary_decision", Decision.INSUFFICIENT.value)),
        matched_path=out.get("matched_path"),
        confidence=Confidence(out.get("confidence", Confidence.low.value)),
        reason=out.get("reason") or "",
        warnings=out.get("warnings") or [],
    )
    return dr

