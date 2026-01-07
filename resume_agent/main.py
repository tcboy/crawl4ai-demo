from __future__ import annotations

import json
import sys
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from resume_agent.agents.executor import build_and_run_dag
from resume_agent.agents.planner import plan_jd_to_job_model, planner_update_rules
from resume_agent.agents.reporter import build_report
from resume_agent.agents.reviewer import review_decision
from resume_agent.models import ContextState, DagResult, JobModel


class GraphState(TypedDict, total=False):
    jd_text: str
    resume_text: str
    job_model: Dict[str, Any] | None
    dag_result: Dict[str, Any] | None
    reflection_log: List[Dict[str, Any]]
    reflection_round: int
    max_reflection_rounds: int

    executor_lenient_mode: bool
    planner_relax_date_rules: bool
    planner_enable_fuzzy: bool

    # reviewer -> router 的内部信号（需要在 state schema 中声明，否则会被丢弃）
    _need_retry: bool

    final_report: Dict[str, Any] | None


def _ensure_defaults(state: GraphState) -> GraphState:
    st = dict(state)
    st.setdefault("jd_text", "")
    st.setdefault("resume_text", "")
    st.setdefault("job_model", None)
    st.setdefault("dag_result", None)
    st.setdefault("reflection_log", [])
    st.setdefault("reflection_round", 0)
    st.setdefault("max_reflection_rounds", 2)
    st.setdefault("executor_lenient_mode", False)
    st.setdefault("planner_relax_date_rules", False)
    st.setdefault("planner_enable_fuzzy", False)
    st.setdefault("_need_retry", False)
    st.setdefault("final_report", None)
    return st  # type: ignore[return-value]


def planner_node(state: GraphState) -> Dict[str, Any]:
    st = _ensure_defaults(state)
    if st["job_model"] is None:
        jm = plan_jd_to_job_model(st["jd_text"])
        return {"job_model": jm.model_dump()}
    return {}


def planner_update_node(state: GraphState) -> Dict[str, Any]:
    st = _ensure_defaults(state)
    if st["job_model"] is None:
        return {}
    jm = JobModel.model_validate(st["job_model"])
    updated = planner_update_rules(
        jm,
        relax_date=bool(st.get("planner_relax_date_rules")),
        enable_fuzzy=bool(st.get("planner_enable_fuzzy")),
    )
    return {
        "job_model": updated.model_dump(),
        # 更新后清空指令，避免重复叠加
        "planner_relax_date_rules": False,
        "planner_enable_fuzzy": False,
    }


def executor_node(state: GraphState) -> Dict[str, Any]:
    st = _ensure_defaults(state)
    jm = JobModel.model_validate(st["job_model"] or {})
    dr = build_and_run_dag(
        job_model=jm,
        resume_text=st["resume_text"],
        lenient_mode=bool(st.get("executor_lenient_mode")),
    )
    return {"dag_result": dr.model_dump()}


def reviewer_node(state: GraphState) -> Dict[str, Any]:
    st = _ensure_defaults(state)
    jm = JobModel.model_validate(st["job_model"] or {})
    dr = DagResult.model_validate(st["dag_result"] or {})
    items, need_retry, directives = review_decision(
        jd_text=st["jd_text"],
        resume_text=st["resume_text"],
        job_model=jm,
        dag_result=dr,
    )
    new_log = st["reflection_log"] + [it.model_dump() for it in items]
    next_round = int(st["reflection_round"]) + 1
    return {
        "reflection_log": new_log,
        "reflection_round": next_round,
        "executor_lenient_mode": bool(directives["executor_lenient_mode"]),
        "planner_relax_date_rules": bool(directives["planner_relax_date_rules"]),
        "planner_enable_fuzzy": bool(directives["planner_enable_fuzzy"]),
        # reviewer 只产出指令；是否重试由路由函数决定
        "_need_retry": bool(need_retry),
    }


def _route_after_review(state: GraphState) -> str:
    st = _ensure_defaults(state)
    need_retry = bool(st.get("_need_retry"))
    if not need_retry:
        return "reporter"
    if int(st["reflection_round"]) >= int(st["max_reflection_rounds"]):
        return "reporter"
    # 有 planner 规则更新则先更新再执行，否则直接重跑 executor
    if st.get("planner_relax_date_rules") or st.get("planner_enable_fuzzy"):
        return "planner_update"
    return "executor"


def reporter_node(state: GraphState) -> Dict[str, Any]:
    st = _ensure_defaults(state)
    dr = DagResult.model_validate(st["dag_result"] or {})
    report = build_report(dag_result=dr)
    return {"final_report": report.model_dump()}


def build_multi_agent_graph():
    g = StateGraph(GraphState)
    g.add_node("planner", planner_node)
    g.add_node("planner_update", planner_update_node)
    g.add_node("executor", executor_node)
    g.add_node("reviewer", reviewer_node)
    g.add_node("reporter", reporter_node)

    g.set_entry_point("planner")
    g.add_edge("planner", "executor")
    g.add_edge("executor", "reviewer")
    g.add_conditional_edges("reviewer", _route_after_review, {
        "planner_update": "planner_update",
        "executor": "executor",
        "reporter": "reporter",
    })
    g.add_edge("planner_update", "executor")
    g.add_edge("reporter", END)
    return g.compile()


def run_once(jd_text: str, resume_text: str) -> ContextState:
    app = build_multi_agent_graph()
    init: GraphState = {
        "jd_text": jd_text,
        "resume_text": resume_text,
        "reflection_round": 0,
        "max_reflection_rounds": 2,
        "reflection_log": [],
        "executor_lenient_mode": False,
        "planner_relax_date_rules": False,
        "planner_enable_fuzzy": False,
    }
    out = app.invoke(init)
    # 组装 ContextState 便于调试/回溯
    ctx = ContextState.model_validate(
        {
            "jd_text": out.get("jd_text", jd_text),
            "resume_text": out.get("resume_text", resume_text),
            "job_model": out.get("job_model"),
            "dag_result": out.get("dag_result"),
            "reflection_log": out.get("reflection_log", []),
            "reflection_round": out.get("reflection_round", 0),
            "max_reflection_rounds": out.get("max_reflection_rounds", 2),
            "executor_lenient_mode": out.get("executor_lenient_mode", False),
            "planner_relax_date_rules": out.get("planner_relax_date_rules", False),
            "planner_enable_fuzzy": out.get("planner_enable_fuzzy", False),
            "final_report": out.get("final_report"),
        }
    )
    return ctx


def main() -> int:
    print("请输入 JD（多行以空行结束）：", file=sys.stderr)
    jd_lines: List[str] = []
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        if line.strip() == "":
            break
        jd_lines.append(line.rstrip("\n"))
    jd_text = "\n".join(jd_lines).strip()
    if not jd_text:
        print("缺少 JD 输入。", file=sys.stderr)
        return 2

    print("请输入 简历（多行以空行结束）：", file=sys.stderr)
    cv_lines: List[str] = []
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        if line.strip() == "":
            break
        cv_lines.append(line.rstrip("\n"))
    resume_text = "\n".join(cv_lines).strip()
    if not resume_text:
        print("缺少 简历 输入。", file=sys.stderr)
        return 2

    ctx = run_once(jd_text, resume_text)
    if not ctx.final_report:
        print("系统未生成 final_report（异常）。", file=sys.stderr)
        return 1
    print(json.dumps(ctx.final_report.model_dump(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

