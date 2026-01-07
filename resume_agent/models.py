from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class Decision(str, Enum):
    Y = "Y"
    N = "N"
    INSUFFICIENT = "信息不足"


class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class EducationLevel(str, Enum):
    # 约定：associate=大专，本科=bachelor
    associate = "associate"
    bachelor = "bachelor"
    master = "master"
    phd = "phd"
    unknown = "unknown"


class EducationRequirement(BaseModel):
    min_level: EducationLevel = Field(
        default=EducationLevel.unknown,
        description="最低学历要求。unknown 表示不限制/未识别。",
    )
    full_time_required: bool = Field(default=False, description="是否要求全日制")
    date_strict: bool = Field(
        default=True, description="教育起止时间是否必须可解析（严格模式）"
    )
    allow_infer_full_time: bool = Field(
        default=False, description="是否允许根据学制/年限推断全日制（宽松模式）"
    )


class CertificateRequirement(BaseModel):
    name: str = Field(description="证书名称/类别（例如：基金从业资格）")
    # 例如 ["科目一", "科目二"]
    must_have_keywords: List[str] = Field(default_factory=list)
    allow_generic_pass: bool = Field(
        default=False,
        description="宽松模式：仅出现‘通过xx考试/持有xx资格’可视为满足（但降低置信度）",
    )

    @field_validator("must_have_keywords")
    @classmethod
    def _dedup(cls, v: List[str]) -> List[str]:
        out: List[str] = []
        for x in v:
            x = x.strip()
            if x and x not in out:
                out.append(x)
        return out


class PathSpec(BaseModel):
    name: str = Field(description="路径名称（用于解释 matched_path）")
    education: EducationRequirement = Field(default_factory=EducationRequirement)
    certificates: List[CertificateRequirement] = Field(default_factory=list)


class JobModel(BaseModel):
    jd_text: str = Field(description="原始JD文本")
    summary: str = Field(default="", description="简要概述（便于日志/展示）")
    # OR 路径：满足任一路径即可 Y
    paths: List[PathSpec] = Field(default_factory=list)

    # 可被 Reviewer 调整的解析/执行策略（仍然是确定性规则开关）
    global_date_strict: bool = Field(default=True)
    global_allow_fuzzy: bool = Field(default=False)

    @field_validator("paths")
    @classmethod
    def _non_empty_paths(cls, v: List[PathSpec]) -> List[PathSpec]:
        if not v:
            raise ValueError("JobModel.paths 不能为空（至少1条路径）")
        return v


class ExtractedEducation(BaseModel):
    level: EducationLevel = EducationLevel.unknown
    full_time: Optional[bool] = None
    start: Optional[str] = None  # 保留原始/标准化字符串
    end: Optional[str] = None
    raw: str = ""
    warnings: List[str] = Field(default_factory=list)


class ExtractedCertificates(BaseModel):
    matched: List[str] = Field(default_factory=list)
    raw_evidence: Dict[str, List[str]] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)


class PathEvaluation(BaseModel):
    path_name: str
    status: Literal["pass", "fail", "unknown"]
    reasons: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class DagResult(BaseModel):
    lenient_mode: bool = False
    extracted_education: ExtractedEducation = Field(default_factory=ExtractedEducation)
    extracted_certificates: ExtractedCertificates = Field(
        default_factory=ExtractedCertificates
    )
    path_evaluations: List[PathEvaluation] = Field(default_factory=list)
    preliminary_decision: Decision = Decision.INSUFFICIENT
    matched_path: Optional[str] = None
    confidence: Confidence = Confidence.low
    reason: str = ""
    warnings: List[str] = Field(default_factory=list)


class ReflectionItem(BaseModel):
    issue: str
    suggestion: str
    severity: Literal["low", "medium", "high"] = "medium"


class ReportModel(BaseModel):
    decision: Decision
    matched_path: Optional[str] = None
    confidence: Confidence
    reason: str
    warnings: List[str] = Field(default_factory=list)


class ContextState(BaseModel):
    jd_text: str = ""
    resume_text: str = ""
    job_model: Optional[JobModel] = None
    dag_result: Optional[DagResult] = None
    reflection_log: List[ReflectionItem] = Field(default_factory=list)
    # 反思循环控制
    reflection_round: int = 0
    max_reflection_rounds: int = 2

    # Reviewer 给 Executor 的执行提示（确定性开关）
    executor_lenient_mode: bool = False
    planner_relax_date_rules: bool = False
    planner_enable_fuzzy: bool = False

    # 最终输出
    final_report: Optional[ReportModel] = None

    def dump_minimal(self) -> Dict[str, Any]:
        """用于 LangGraph 状态流转的 dict（避免传递过重对象）。"""
        return self.model_dump()

