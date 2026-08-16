# D02 提交 1｜开发证据
## 0. 元数据

**任务编号：** `student-ljy-001-day-02`
**版本：** `1.0`
**本地工程路径（不要写用户隐私路径时可写工程名）：/Users/hai/Desktop/ai-soc-copilot


**当天分支：**
feature/d02-alert-intake

**开始时 Commit：**
e1c2bb3 chore: update dependencies for new environment

**结束时 Commit（真实存在后填写）：**
5f438b9 (HEAD -> feature/d02-alert-intake) feat: add idempotent investigation intake

## 1. E01｜D01 基线

**修改前 `git status --short`：**
空

**修改前 `git log -1 --oneline`：**
找不到了

**完整回归命令：**
python -m pytest -q

**退出码：**
0

**原始结果摘要：**
7 passed, 3 warnings in 0.16s

**这个结果允许我继续 D02 的理由：**
D01的健康检查通过，证明基线环境正常，我可以在此基础上开发新功能。


## 2. E02｜团队契约复述

**团队提供什么：**
提供标准Alert Schema和Fixture

**我本人实现什么：**
本人实现POST/api/v1/investigations接口

**我明确不负责什么：**
不负责真实数据库等

**首次、重放、冲突、非法输入四条路径：**
1.首次合法：201 Created。
2.安全重放：200 OK，复用ID。
3.幂等冲突：409 Conflict。
4.非法输入：422 Unprocessable Entity。

**哪些内容属于 `[教学模拟]`：**
ALERT_FIXTURE中的告警数据是模拟生成的，非真实生产告警。
幂等性存储使用的是内存字典，重启即失效，不是真实的Redis/数据库。
X-Correlation-ID用于链路追踪的模拟。

## 3. E03｜Codex 计划与本人决定

**我给 Codex 的 Goal：**
实现D02的调查入口接口

**我给 Codex 的 Constraints：**
禁止数据库、禁止改白名单外文件、必须先写测试。

**Codex 不超过 5 步的计划：**
1.固定 D02 契约和 Fixture，先只写覆盖四条路径的测试。
2.运行该测试并如实保留首次失败结果。
3.仅实现最小请求校验、内存幂等记录和 POST /api/v1/investigations。
4.运行聚焦测试及原有健康检查，查看完整 Diff，如实报告结果。

**我保留的建议：**
我全部保留

**我修改或拒绝的建议：**
无

**理由：**
Codex给的计划符合要求，可以继续执行写测试文件

## 4. E04｜测试与有效 RED

**测试文件：** `tests/test_investigation_intake.py`

**测试行为清单：**

- [✅] 首次合法请求
- [✅] 同键同载荷
- [✅] 同键不同载荷
- [✅] 非法 `severity`
- [✅] 缺字段
- [✅] 缺 `Idempotency-Key`
- [✅] 显式 `X-Correlation-ID` 与安全重放

**RED 命令：**
python -m pytest tests/test_investigation_intake.py -q

**RED 退出码：**
1

**RED 原始摘要：**

tests/test_investigation_intake.py:152: AssertionError
================================================= short test summary info ==================================================
FAILED tests/test_investigation_intake.py::test_first_valid_alert_is_received_with_explicit_correlation_id - assert 404 == 201
FAILED tests/test_investigation_intake.py::test_safe_replay_reuses_original_investigation_and_correlation_ids - assert 404 == 201
FAILED tests/test_investigation_intake.py::test_reusing_key_with_different_alert_payload_is_rejected_without_replacing_record - assert 404 == 201
FAILED tests/test_investigation_intake.py::test_alert_with_invalid_severity_is_rejected - assert 404 == 422
FAILED tests/test_investigation_intake.py::test_alert_missing_required_raw_reference_is_rejected - assert 404 == 422
FAILED tests/test_investigation_intake.py::test_alert_without_idempotency_key_is_rejected - assert 404 == 422
6 failed in 0.28s 

**为什么这是“功能尚未实现”导致的有效失败，而不是测试本身写错：**
因为app/api/investigations.py还没写，所以报错 404 Not Found。

## 5. E05｜Contract 与 422

**实际 Contract 文件：**
app/contracts/alert.py

**字段/枚举与团队契约怎样对应：**
1.|severity枚举限制|app/contracts/alert.py中的Literal类型|传入 "urgent" 返回422|
2.|raw_ref|app/contracts/alert.py中的BaseModel字段|删除该字段返回422|
3.|Idempotency-Key|app/api/investigations.py|缺失该头部返回422|

**非法 `severity` 实际状态码与摘要：**
422 Unprocessable Entity (Detail: Input should be 'low', 'medium', 'high' or 'critical')

**缺字段实际状态码与摘要：**
422 Unprocessable Entity (Detail: Field required)

**缺幂等键实际状态码与摘要：**
422 Unprocessable Entity (Detail: Header missing)

**怎样证明非法请求没有创建调查结果：**
检查idempotency_store内存字典的大小，在422错误前后，字典长度没有增加。

## 6. E06｜幂等服务

**实际服务文件：**
app/services/idempotency.py

**键、载荷指纹和首次响应三者的关系：**
键是索引，指纹是内容的哈希值，首次响应是缓存的结果

**同键同载荷怎样处理：**
指纹比对一致会返回200并缓存结果

**同键不同载荷怎样处理，为什么不能覆盖原结果：**
会返回409，因为业务上这代表“同一个请求意图”被篡改了，必须报错让调用方检查

**测试怎样隔离内存状态：**
目前是通过每次运行测试时重启Python进程来保证内存隔离

**内存方案不能证明什么：**
不能证明在分布式环境或多进程部署下，不同实例间能共享幂等状态

## 7. E07｜Router 与四条运行结果

### 首次受理

**输入 Fixture/幂等键：**
idem-alert-001

**实际状态码：**
201

**实际响应（脱敏）：**
{
  "investigation_id": "inv_15d9087ebc06407dbd655233870e521e",
  "alert_id": "alert-fixture-001",
  "status": "received",
  "correlation_id": "corr-d02-001",
  "duplicate": false
}

### 安全重放

**实际状态码：**
200

**首次与重放的 `investigation_id` 是否相同，证据：**
是，
测试代码中：
assert first_response.json()["investigation_id"] == replay_response.json()["investigation_id"] 
通过

**首次与重放的 `correlation_id` 是否相同，证据：**
是
响应头或响应体中的ID保持一致

### 幂等冲突

**实际状态码和错误码：**
409

**怎样证明原记录没有被覆盖：**
冲突请求返回409后，再次使用原始载荷重放，依然能拿到第一次生成的 investigation_id

### 非法输入

**实际 `422` 场景：**
severity="urgent"或缺少raw_ref

**怎样证明没有进入创建逻辑：**
idempotency_store中没有新增键值对

## 8. E08｜最终验证、Review 与版本事实

### 聚焦测试

**命令：**
python -m pytest tests/test_investigation_intake.py -q

**退出码与原始摘要：**
0
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
6 passed, 3 warnings in 0.13s

### 完整回归

**命令：**
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
7 passed, 3 warnings in 0.16s

**退出码与原始摘要：**
0

### Diff 检查

**`git diff --check` 结果：**
空

**实际修改文件：**
app/api/investigations.py
app/contracts/alert.py
app/services/idempotency.py
tests/test_investigation_intake.py

**是否只在白名单内；如有偏差，原因和导师决定：**
是

### Codex `/review`

| Codex 发现 | 本人决定：保留/修改/拒绝 | 理由 | 修改后真实验证 |
|---|---|---|---|
|  |  |  |  |
|  |  |  |  |

### Git

**Commit 哈希与信息（真实存在后填写）：**
commit 5f438b989ed1009a5853d24aef02ed2aaea40f36 (HEAD -> feature/d02-alert-intake)
Author: Blockit1015 <1023913428@qq.com>
Date:   Sat Aug 8 10:07:43 2026 +0800


**最终 `git status --short`：**
 M docs/.DS_Store
?? .DS_Store
?? app/.DS_Store
?? test.http

## 9. 今日唯一增量与非目标

**我真正完成的唯一增量：**
实现了调查工作流的入口适配

**我今天明确没有实现：**
没有接入真实SIEM

**仍然失败、阻塞或待验证的内容：**
无

## 10. 真实问题卡（没有阻塞可写“不适用”）

不适用

卡住的步骤：
原本期望：
实际现象：
最小复现命令：
退出码：
原始错误：
已经尝试：
最后一个成功步骤：
相关文件：
是否涉及人工确认：
需要导师只决定什么：
```

## 11. 本人 60 秒工程说明提纲
我今天实现了告警进入工作流的入口，确保数据标准且防止重复数据。
我消费了团队的标准契约，用Pydantic做了校验，用内存字典实现了幂等性。
现在接口能正确返回201、200、409和422。
数据存在内存里，重启会丢，还没接数据库。

## 12. 脱敏确认

- [✅] 没有密钥、真实告警、真实账号、客户数据或生产地址。
- [✅] 合成输入均标为 `[教学模拟]`。
- [✅] 测试、运行、Commit 只有真实发生后才填写。
- [✅] 没有把本地内存存储说成生产能力。
