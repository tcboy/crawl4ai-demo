## 简历评估系统（ReAct + Multi-Agent + LangGraph）

本项目实现一个**基于 ReAct（Reasoning-Action-Reflection）与 Multi-Agent 架构**的简历评估系统：

- **Planner**：仅用于将 JD 结构化为 `JobModel`（优先调用 OpenAI `gpt-4o`；无 Key 时降级为规则解析）
- **Executor**：基于 `JobModel` 动态构建并执行 LangGraph DAG（纯规则抽取与判定，**不使用 LLM 做决策**）
- **Reviewer**：基于规则做“字段缺失/逻辑冲突/过于激进”检查，最多 **2 次**触发修正循环
- **Reporter**：输出严格 JSON（`Y` / `N` / `信息不足`）

### 安装

```bash
pip3 install -r requirements.txt
```

### 运行

交互式输入 JD 与简历（均以空行结束）：

```bash
python3 -m resume_agent.main
```

可选：如果希望 Planner 使用 OpenAI 结构化 JD，设置环境变量：

```bash
export OPENAI_API_KEY="你的key"
```

### 示例

JD：

> 需基金从业资格证（科目一+二），全日制大专；若无证，则需全日制本科。

简历：

> 2019 – 2022 XX学院 大专  
> 通过基金从业资格考试

系统会在 Reviewer 触发“放宽时间/启用证书宽松匹配”的修正循环后，输出 `decision=Y`（通常 `confidence=medium` 并附带 warnings）。


