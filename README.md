# EduCS Insight Agent

EduCS Insight Agent 是一个面向 AI 教育产品客户成功场景的数据分析与数据初始化智能体。

项目来源于 AI 教育产品客户成功实习场景，使用模拟脱敏数据复现以下工作流：

- 学校、产品、教师、学生维度的使用率分析
- 项目启动、培训、验收状态跟踪
- 交付一组/二组/三组的培训达标率分析
- 客户成功人员达标率下降诊断
- 客户成功月报生成
- 海班慧成绩单导入模板清洗
- 隐私脱敏、token 压缩与 LLM 调用缓存

## 项目定位

这不是一个简单的“上传 Excel 让大模型总结”的 Demo。

系统先用 Pandas / SQLite 完成确定性计算，再由 Agent 根据用户问题选择工具，最后只把聚合摘要、RAG 检索结果或诊断结论发送给 DeepSeek 生成报告。

```text
原始 CSV / Excel
  -> 数据校验与加载
  -> Pandas 指标计算
  -> SQLite 问数工具
  -> RAG 业务知识检索
  -> 隐私脱敏
  -> token 压缩摘要
  -> DeepSeek 月报生成
  -> 本地缓存复用
```

## 技术栈

- Python
- Streamlit
- Pandas
- SQLite
- LangGraph
- LangChain Core
- Chroma
- DeepSeek API
- RAG
- Pytest

## 功能模块

### 1. 客户成功看板

- 项目交付总览：未启动、已启动、已培训、已验收
- 产品使用率：星学伴、星乐读、星未来、鸿儒教研、海班慧
- 学校使用排名：学校类型、教师使用率、学生使用率、综合使用率
- 交付组培训达标率
- 客户成功人员培训达标率
- 看板表格使用中文字段展示，并将业务排名 `rank` 与学校编号、人员编号等原始主键分离，避免用户误读 DataFrame 索引或数据库编号

### 2. Agent 问数与月报

支持自然语言问题：

```text
为什么客户成功A2026-06达标率下降了？
2026-06星学伴在不同学校的使用排名
客户成功A负责的项目验收情况
交付一组人员项目数
培训达标率口径和40%阈值是什么
这个系统如何节约token并保护隐私
```

系统会通过 LangGraph 工作流执行：

```text
route_intent
  -> execute_tool
  -> prepare_response
```

底层工具包括：

- SQL 学校产品使用排名
- SQL 客户成功项目验收统计
- SQL 交付组人员负载统计
- Pandas 达标率下降诊断
- RAG 业务口径检索
- DeepSeek 月报生成

### 3. 海班慧成绩单清洗

支持将学校原始成绩单清洗为两类结果。

第一类是年级成绩汇总宽表，适合处理一整个年级、多班级、多科目的成绩单：

```text
姓名、学号、总分、联排、校排、班排、语文、数学、英语、物理、化学、生物、政治、历史、地理、班级
```

第二类是后台导入长表，适合系统导入或进一步数据建模：

```text
学校名称、年级、班级、学生姓名、学号、考试名称、科目、成绩、满分、考试时间
```

清洗能力：

- 字段映射：姓名/学生/学生姓名
- 班级格式标准化：三年级1班、三(1)班、三（一）班、三年级二班、301
- 多科目宽表处理：语文、数学、英语、物理、化学、生物、政治、历史、地理
- 总分与排名处理：原表存在总分/联排/校排/班排时优先保留，缺失时按当前年级数据自动计算校排和班排
- 缺考和空值处理
- 宽表转长表：语文/数学/英语列转为科目行
- 重复学生科目检测
- 异常报告输出
- CSV 下载使用 `utf-8-sig` 编码，减少 Windows Excel 双击打开时的中文乱码问题

## 示例数据

`examples/` 目录提供了 3 份用于演示清洗能力的脱敏脏数据：

```text
examples/dirty_exam_single_subject.csv
examples/dirty_exam_20_rows.csv
examples/dirty_grade_report_multi_subject.csv
```

其中 `dirty_grade_report_multi_subject.csv` 更接近真实年级成绩单，包含多个班级、多科成绩、总分、联排、校排、班排、重复学生和缺失学号等情况。

## 隐私与成本设计

教育场景涉及学校、教师、学生和客户成功人员数据，项目加入了以下机制：

- `.env` 管理 API Key，并通过 `.gitignore` 避免误提交
- 学校、人员、学生、学号等敏感字段在进入 LLM 前脱敏
- 原始明细表不直接发送给 LLM
- 只发送聚合指标、诊断信号和 RAG 片段
- 相同月报摘要命中本地缓存，避免重复消耗 token

## 快速启动

```powershell
cd D:\agent_projects\educs_insight_agent
.\.venv\Scripts\Activate.ps1
streamlit run app.py --server.port 8502
```

访问：

```text
http://localhost:8502
```

如果需要从零安装：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
copy .env.example .env
python scripts\generate_sample_data.py
streamlit run app.py --server.port 8502
```

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

当前测试覆盖：

- 指标计算
- 达标率下降诊断
- 问数意图识别
- SQL 工具调用
- RAG 检索
- 成绩单清洗
- 隐私脱敏
- LangGraph 工作流

## SQL 查询文件

项目将结构化问数 SQL 独立放在 `sql/` 目录：

```text
sql/product_school_ranking.sql
sql/acceptance_status_by_staff.sql
sql/group_workload.sql
```

`src/query_agent.py` 根据用户意图选择对应 SQL 文件，并通过 `src/sql_store.py` 执行查询。

## RAG 检索设计

项目中的 RAG 不用于结构化指标计算，而用于业务知识检索，包括培训达标规则、隐私/token 策略、风险诊断手册和历史月报备注。

当前实现包含：

- 使用 LangChain Core `Document` 抽象知识库文档
- 按 Markdown 标题和段落进行文档分段，控制单个 chunk 长度
- 使用本地哈希 Embedding 生成 384 维向量，避免额外下载大模型
- 使用 Chroma 持久化向量库，默认存储在 `data/chroma`
- 检索后结合关键词 overlap 做轻量 rerank，提高业务口径命中率
- 如果 Chroma 环境异常，会降级为关键词 fallback，保证项目可运行

## 设计说明

项目采用“确定性计算 + LLM 生成”的混合架构。结构化指标由 Pandas/SQL 在本地完成，非结构化业务规则由 RAG 检索补充，LLM 只负责将聚合后的结果组织成可读报告。

### 核心原则

```text
LLM 不直接处理原始表格。
结构化数据由 Pandas/SQL 计算。
非结构化业务规则由 RAG 检索。
LangGraph 负责任务编排。
DeepSeek 负责生成可读报告。
```

### 扩展方式

项目中的工具边界比较清晰：

- 新增结构化问数任务：添加 SQL 文件并在 `src/query_agent.py` 中配置意图路由
- 新增业务规则：向 `data/knowledge/` 添加 Markdown 文档
- 新增指标：在 `src/metrics.py` 中扩展 Pandas 计算逻辑
- 新增工作流节点：在 `src/workflow.py` 中扩展 LangGraph 节点
