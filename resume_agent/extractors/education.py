from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Tuple

from resume_agent.models import EducationLevel, ExtractedEducation


_RE_YEAR_RANGE = re.compile(
    r"(?P<y1>19\d{2}|20\d{2})\s*[-–—~至]\s*(?P<y2>19\d{2}|20\d{2})"
)
_RE_YM_RANGE = re.compile(
    r"(?P<y1>19\d{2}|20\d{2})[./\-年]\s*(?P<m1>0?[1-9]|1[0-2])"
    r"\s*[-–—~至]\s*"
    r"(?P<y2>19\d{2}|20\d{2})[./\-年]\s*(?P<m2>0?[1-9]|1[0-2])"
)


def _detect_level(text: str) -> EducationLevel:
    t = text.lower()
    # 中文优先
    if "博士" in text or "phd" in t:
        return EducationLevel.phd
    if "硕士" in text or "研究生" in text or "master" in t:
        return EducationLevel.master
    if "本科" in text or "bachelor" in t:
        return EducationLevel.bachelor
    if "大专" in text or "专科" in text or "associate" in t:
        return EducationLevel.associate
    return EducationLevel.unknown


def _infer_full_time(text: str) -> Optional[bool]:
    # 明示优先
    if "全日制" in text:
        return True
    if "非全" in text or "非全日制" in text or "成人" in text or "函授" in text or "自考" in text:
        return False
    return None


def _pick_education_line(resume_text: str) -> str:
    # 经验规则：优先包含“学院/大学/学校/本科/大专/专科”等关键词的行
    lines = [ln.strip() for ln in resume_text.splitlines() if ln.strip()]
    edu_lines = []
    for ln in lines:
        if any(k in ln for k in ["学院", "大学", "学校", "本科", "大专", "专科", "硕士", "博士"]):
            edu_lines.append(ln)
    if edu_lines:
        # 选择最可能的教育条目：含时间 or 含学历级别
        def score(x: str) -> int:
            s = 0
            if _RE_YM_RANGE.search(x) or _RE_YEAR_RANGE.search(x):
                s += 3
            if _detect_level(x) != EducationLevel.unknown:
                s += 2
            if "全日制" in x:
                s += 1
            return s

        edu_lines.sort(key=score, reverse=True)
        return edu_lines[0]
    # 实在没有，退化为整段文本（但会更不稳定）
    return resume_text


def _extract_dates(line: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    返回 (start, end, warning)
    start/end 为原始截取字符串，warning 为可选警告信息
    """
    m = _RE_YM_RANGE.search(line)
    if m:
        start = f"{m.group('y1')}.{int(m.group('m1')):02d}"
        end = f"{m.group('y2')}.{int(m.group('m2')):02d}"
        return start, end, None

    m = _RE_YEAR_RANGE.search(line)
    if m:
        start = f"{m.group('y1')}"
        end = f"{m.group('y2')}"
        return start, end, "教育时间仅为年份区间（无月），可能需要宽松推断"

    return None, None, "未识别到教育起止时间"


def extract_education(*, resume_text: str, date_strict: bool, allow_infer_full_time: bool) -> ExtractedEducation:
    line = _pick_education_line(resume_text)
    level = _detect_level(line)
    full_time = _infer_full_time(line)
    start, end, warn = _extract_dates(line)

    out = ExtractedEducation(level=level, full_time=full_time, start=start, end=end, raw=line)
    if warn:
        out.warnings.append(warn)

    # 严格模式：缺时间视为未知（交给评估器）
    if date_strict and (start is None or end is None):
        out.warnings.append("严格模式下教育时间不完整，相关判断将转为未知")

    # 宽松推断：如果只有年份，且年限在 [2,5]，可推断全日制为 True（仍可能不确定）
    if allow_infer_full_time and full_time is None:
        m = _RE_YEAR_RANGE.search(line)
        if m:
            y1 = int(m.group("y1"))
            y2 = int(m.group("y2"))
            span = max(0, y2 - y1)
            if 2 <= span <= 5:
                out.full_time = True
                out.warnings.append("宽松模式：根据学制年限推断为全日制（不完全确定）")

    return out

