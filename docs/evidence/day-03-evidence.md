## E01
**命令**
python -m pytest tests/test_health.py tests/test_investigation_intake.py -q
**实际输出摘要**
7 passed, 3 warnings in 0.18s
**涉及的文件**
- app/main.py
- app/api/investigations.py
- app/services/idempotency.py
- tests/test_investigation_intake.py
**区分**
- investigation_id：调查任务ID，系统自己生成，在每条记录的 response 中
- correlation_id：追踪标识，系统自己生成，在每条记录的 response 中
- idempotency_key：防重放字典的KEY，用来防止重复提交，这是发起的请求（也就是外部系统或测试代码）传输过来就含有的，不是我的系统生成的。读取过程是：遍历防重放字典中的所有记录。查看每条记录的response["investigation_id"]

## E02｜RED 测试
**事实状态：**
1.场景一失败：实际 404，期望200。说明context路由尚未实现，测试暴露了功能缺口
2.场景二通过：当前不存在的路由本身就返回404，且没有三个标识，这是已确认接受的暂时通过，不能单独证明未知investigation查询逻辑已经实现
3.场景三失败：app.adapters.case_evidence_stub尚未创建，该路径是第三步计划的产物
**测试文件：**
tests/test_case_evidence_integration.py
**执行命令：**
python -m pytest tests/test_case_evidence_integration.py -q
**结果摘要：**
2 failed, 1 passed, 1 warning in 0.11s
**三条用例名**
1. test_existing_investigation_returns_frozen_context_with_saved_correlation_id
2. test_unknown_investigation_returns_404_without_context_identifiers
3. test_existing_investigation_returns_503_when_stub_is_unavailable

## E03
**三条职责明确的路径与每层职责**
- Contract（数据契约）—app/contracts/case_evidence.py
定义数据结构，告诉系统：团队那边传过来的数据长什么样（CaseBinding、EvidenceRef），我们返回的数据长什么样（ContextResult 、 DependencyError）
- Port（接口）—app/ports/case_evidence.py
定义消费这些对象所需的最小读取接口
- Stub（教学替身）—app/adapters/case_evidence_stub.py
这是一个模拟器，它实现了上面的 CaseEvidencePort 接口，它有一个开关 mode，如果是 available，它就返回任务书里写死的假数据（inv-demo-001等）；如果是 unavailable，它就抛出一个约定好的503错误。
**真实测试输出**
(.venv) hai@Mac ai-soc-copilot % python -m pytest tests/test_case_evidence_integration.py -q

======================================= short test summary info ========================================
FAILED tests/test_case_evidence_integration.py::test_existing_investigation_returns_frozen_context_with_saved_correlation_id - assert 404 == 200
FAILED tests/test_case_evidence_integration.py::test_existing_investigation_returns_503_when_stub_is_unavailable - assert 404 == 503
2 failed, 1 passed, 1 warning in 0.16s

## E04
**真实测试输出**
(.venv) hai@Mac ai-soc-copilot % python -m pytest tests/test_case_evidence_integration.py -q
3 passed, 1 warning in 0.10s
**三种场景**
| 测试场景 | HTTP 状态码 | 字段存在/不存在情况 | correlation_id 验证 |

|场景一：成功| 200 OK|存在：`status`, `case_id`, `evidence_refs`|响应体中的`correlation_id`与准备阶段保存的`saved_correlation_id`严格相等|
|场景二：未知ID|404 Not Found|不存在：`correlation_id`, `case_id`, `evidence_refs`| 不生成correlation_id|
|场景三：不可用| 503 Service Unavailable|存在：`error_code`, `message`，不存在：`case_id`, `evidence_refs`|响应体中的`correlation_id`与准备阶段保存的 `saved_correlation_id`严格相等|

## E05-回归部分
**聚焦测试**
*命令：*
python -m pytest tests/test_case_evidence_integration.py -q
echo $?
*输出摘要：*
3 passed, 1 warning in 0.09s
*退出码*
0
*事实核对：（代码本身核对的）*
- 成功200与503的 correlation_id相同
- 404 未生成任何关联、case 或 evidence 标识
**全量回归**
*命令：*
python -m pytest tests/test_health.py tests/test_investigation_intake.py tests/test_case_evidence_integration.py -q
echo $?
*输出摘要：*
10 passed, 1 warning in 0.11s
*退出码*
0

