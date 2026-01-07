from __future__ import annotations

import re
from typing import Any, Dict, List

from resume_agent.models import (
    CertificateRequirement,
    EducationLevel,
    EducationRequirement,
    JobModel,
    PathSpec,
)
from resume_agent.utils import OpenAIJsonError, openai_structured_parse, parse_with_pydantic


_JOBMODEL_SCHEMA_HINT = """
{
  "jd_text": "string",
  "summary": "string",
  "paths": [
    {
      "name": "string",
      "education": {
        "min_level": "associate|bachelor|master|phd|unknown",
        "full_time_required": true,
        "date_strict": true,
        "allow_infer_full_time": false
      },
      "certificates": [
        {
          "name": "string",
          "must_have_keywords": ["string"],
          "allow_generic_pass": false
        }
      ]
    }
  ],
  "global_date_strict": true,
  "global_allow_fuzzy": false
}
""".strip()


def _detect_education_req(text: str) -> EducationRequirement:
    min_level = EducationLevel.unknown
    if "博士" in text:
        min_level = EducationLevel.phd
    elif "硕士" in text or "研究生" in text:
        min_level = EducationLevel.master
    elif "本科" in text:
        min_level = EducationLevel.bachelor
    elif "大专" in text or "专科" in text:
        min_level = EducationLevel.associate

    return EducationRequirement(
        min_level=min_level,
        full_time_required=("全日制" in text),
        date_strict=True,
        allow_infer_full_time=False,
    )


def _detect_cert_reqs(text: str) -> List[CertificateRequirement]:
    out: List[CertificateRequirement] = []
    # 基金从业资格（示例）
    if "基金从业" in text:
        kws: List[str] = []
        if "科目一" in text or "科目1" in text:
            kws.append("科目一")
        if "科目二" in text or "科目2" in text:
            kws.append("科目二")
        # 常见写法：科目一+二 / 1+2
        if re.search(r"科目\s*[一1]\s*\+\s*[二2]", text):
            if "科目一" not in kws:
                kws.append("科目一")
            if "科目二" not in kws:
                kws.append("科目二")
        out.append(
            CertificateRequirement(
                name="基金从业资格",
                must_have_keywords=kws,
                allow_generic_pass=True,
            )
        )
    return out


def heuristic_parse_jd(jd_text: str) -> JobModel:
    """
    无 OpenAI key 时的确定性降级解析：
    - 支持简单“；若无…则…”的双路径 OR
    - 否则生成单路径
    """
    jd = jd_text.strip()
    parts = re.split(r"[；;]\s*", jd)

    # 识别“若无/否则/如无”触发的 OR 结构
    primary = parts[0] if parts else jd
    secondary = ""
    for p in parts[1:]:
        if any(k in p for k in ["若无", "如无", "否则", "若没有", "没有证"]):
            secondary = p
            break

    paths: List[PathSpec] = []
    if secondary:
        # 路径1：primary
        p1_edu = _detect_education_req(primary)
        p1_certs = _detect_cert_reqs(primary)
        p1_name = "持证路径" if p1_certs else "主路径"
        paths.append(PathSpec(name=p1_name, education=p1_edu, certificates=p1_certs))

        # 路径2：secondary（通常是“无证则本科”这类）
        p2_edu = _detect_education_req(secondary)
        p2_certs = _detect_cert_reqs(secondary)
        # 如果二段里没写证书，视为“无证路径”：不要求证书
        p2_name = "无证路径" if not p2_certs else "备选路径"
        paths.append(PathSpec(name=p2_name, education=p2_edu, certificates=p2_certs))
        summary = f"识别到 OR 路径（{p1_name}/{p2_name}）"
    else:
        edu = _detect_education_req(jd)
        certs = _detect_cert_reqs(jd)
        name = "持证路径" if certs else "默认路径"
        paths.append(PathSpec(name=name, education=edu, certificates=certs))
        summary = "单路径要求"

    return JobModel(jd_text=jd_text, summary=summary, paths=paths)


def plan_jd_to_job_model(jd_text: str) -> JobModel:
    """
    Planner Agent：JD -> JobModel
    - 优先用 OpenAI (gpt-4o) 做结构化（仅解析，不做决策）
    - 若无 key 或失败，则降级到 heuristic_parse_jd（确定性）
    """
    system_prompt = (
        "你是招聘JD结构化解析器。你的任务是把中文JD解析为结构化JSON，"
        "只输出 JSON object。不要给出录用/淘汰结论。"
    )
    user_prompt = f"请将以下 JD 解析为 JobModel：\n{jd_text}"

    try:
        data = openai_structured_parse(
            model="gpt-4o",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_schema_hint=_JOBMODEL_SCHEMA_HINT,
            temperature=0.0,
        )
        jm = parse_with_pydantic(JobModel, data)
        # 若 LLM 未填 summary，给一个默认
        if not jm.summary:
            jm.summary = "OpenAI 结构化解析"
        return jm
    except OpenAIJsonError:
        return heuristic_parse_jd(jd_text)


def planner_update_rules(job_model: JobModel, *, relax_date: bool, enable_fuzzy: bool) -> JobModel:
    """
    Planner 的“规则优化”是确定性的：只修改 JobModel 内的开关/要求，不产生最终决策。
    """
    jm = job_model.model_copy(deep=True)
    if relax_date:
        jm.global_date_strict = False
        for p in jm.paths:
            p.education.date_strict = False
            p.education.allow_infer_full_time = True
        jm.summary = (jm.summary + " | Planner: 放宽教育时间/启用全日制推断").strip(" |")
    if enable_fuzzy:
        jm.global_allow_fuzzy = True
        for p in jm.paths:
            for c in p.certificates:
                c.allow_generic_pass = True
        jm.summary = (jm.summary + " | Planner: 启用证书宽松匹配").strip(" |")
    return jm

