# E01 - 基线回归测试
*运行全量回归测试*
指令：python -m pytest tests/ -v
输出：
collected 10 items                                                                                                                                      

tests/test_case_evidence_integration.py::test_existing_investigation_returns_frozen_context_with_saved_correlation_id PASSED                        [ 10%]
tests/test_case_evidence_integration.py::test_unknown_investigation_returns_404_without_context_identifiers PASSED                                  [ 20%]
tests/test_case_evidence_integration.py::test_existing_investigation_returns_503_when_stub_is_unavailable PASSED                                    [ 30%]
tests/test_health.py::test_health_returns_fixed_contract PASSED                                                                                     [ 40%]
tests/test_investigation_intake.py::test_first_valid_alert_is_received_with_explicit_correlation_id PASSED                                          [ 50%]
tests/test_investigation_intake.py::test_safe_replay_reuses_original_investigation_and_correlation_ids PASSED                                       [ 60%]
tests/test_investigation_intake.py::test_reusing_key_with_different_alert_payload_is_rejected_without_replacing_record PASSED                       [ 70%]
tests/test_investigation_intake.py::test_alert_with_invalid_severity_is_rejected PASSED                                                             [ 80%]
tests/test_investigation_intake.py::test_alert_missing_required_raw_reference_is_rejected PASSED                                                    [ 90%]
tests/test_investigation_intake.py::test_alert_without_idempotency_key_is_rejected PASSED                                                           [100%]

============================================================== 10 passed, 1 warning in 0.19s ==============================================================
*指向路径*
/app/services/context_preparation.py
/tests/test_case_evidence_integration.py

# E02 - RED
*首先要得到已准备上下文，我运行了以下命令：*
python -c 'from fastapi.testclient import TestClient; from app.main import app; from app.adapters.case_evidence_stub import case_evidence_stub; case_evidence_stub.set_mode("available"); c=TestClient(app); alert={"alert_id":"alert-fixture-001","source":"training-siem","occurred_at":"2026-07-30T01:00:00Z","severity":"high","title":"Repeated failed sign-in in training tenant","asset_id":"asset-fixture-001","raw_ref":"fixture://alerts/alert-fixture-001"}; intake=c.post("/api/v1/investigations",headers={"Idempotency-Key":"idem-d04-inspect-001","X-Correlation-ID":"corr-d04-inspect-001"},json=alert); print("D02 status:", intake.status_code); print("D02 body:", intake.json()); investigation_id=intake.json()["investigation_id"]; context=c.post(f"/api/v1/investigations/{investigation_id}/context"); print("D03 status:", context.status_code); print("D03 body:", context.json())'
*得到真实输出：*
D02 status: 201
D02 body: {'investigation_id': 'inv_b863a71c0ce84cfcb7dce9968520793e', 'alert_id': 'alert-fixture-001', 'status': 'received', 'correlation_id': 'corr-d04-inspect-001', 'duplicate': False}
D03 status: 200
D03 body: {'status': 'CONTEXT_READY', 'investigation_id': 'inv_b863a71c0ce84cfcb7dce9968520793e', 'case_id': 'case-demo-001', 'evidence_refs': ['ev-demo-001'], 'correlation_id': 'corr-d04-inspect-001'}
*提取出需要的字段：*
case_id: case-demo-001
evidence_refs: ["ev-demo-001"]
correlation_id: corr-d04-inspect-001
state: CONTEXT_READY
*写好后测试指令*
python -m pytest tests/test_agent_minimal_flow.py -q
*输出摘要*
FAILED tests/test_agent_minimal_flow.py::test_ready_context_calls_read_only_tool_once_and_finishes_enriched - ModuleNotFoundError: No module named 'app.adapters.read_only_tool_stub'
FAILED tests/test_agent_minimal_flow.py::test_missing_required_context_input_stops_in_manual_without_calling_tool[missing-case-id] - ModuleNotFoundError: No module named 'app.adapters.read_only_tool_stub'
FAILED tests/test_agent_minimal_flow.py::test_missing_required_context_input_stops_in_manual_without_calling_tool[missing-evidence-refs] - ModuleNotFoundError: No module named 'app.adapters.read_only_tool_stub'
FAILED tests/test_agent_minimal_flow.py::test_missing_required_context_input_stops_in_manual_without_calling_tool[missing-correlation-id] - ModuleNotFoundError: No module named 'app.adapters.read_only_tool_stub'
FAILED tests/test_agent_minimal_flow.py::test_missing_required_context_input_stops_in_manual_without_calling_tool[missing-case-id-and-evidence-refs] - ModuleNotFoundError: No module named 'app.adapters.read_only_tool_stub'
FAILED tests/test_agent_minimal_flow.py::test_missing_required_context_input_stops_in_manual_without_calling_tool[missing-case-id-and-correlation-id] - ModuleNotFoundError: No module named 'app.adapters.read_only_tool_stub'
FAILED tests/test_agent_minimal_flow.py::test_missing_required_context_input_stops_in_manual_without_calling_tool[missing-evidence-refs-and-correlation-id] - ModuleNotFoundError: No module named 'app.adapters.read_only_tool_stub'
FAILED tests/test_agent_minimal_flow.py::test_missing_required_context_input_stops_in_manual_without_calling_tool[missing-all-context-inputs] - ModuleNotFoundError: No module named 'app.adapters.read_only_tool_stub'
FAILED tests/test_agent_minimal_flow.py::test_tool_timeout_stops_in_manual_without_retry - ModuleNotFoundError: No module named 'app.adapters.read_only_tool_stub'
FAILED tests/test_agent_minimal_flow.py::test_zero_budget_before_call_stops_in_manual_without_calling_tool - ModuleNotFoundError: No module named 'app.adapters.read_only_tool_stub'
FAILED tests/test_agent_minimal_flow.py::test_second_tool_call_attempt_stops_in_manual_without_another_call - ModuleNotFoundError: No module named 'app.adapters.read_only_tool_stub'
FAILED tests/test_agent_minimal_flow.py::test_non_entry_state_cannot_start_another_successful_run[restart-from-enriching] - ModuleNotFoundError: No module named 'app.adapters.read_only_tool_stub'
FAILED tests/test_agent_minimal_flow.py::test_non_entry_state_cannot_start_another_successful_run[restart-from-enriched] - ModuleNotFoundError: No module named 'app.adapters.read_only_tool_stub'
FAILED tests/test_agent_minimal_flow.py::test_non_entry_state_cannot_start_another_successful_run[restart-from-manual] - ModuleNotFoundError: No module named 'app.adapters.read_only_tool_stub'
FAILED tests/test_agent_minimal_flow.py::test_success_trace_does_not_skip_enriching_state - ModuleNotFoundError: No module named 'app.adapters.read_only_tool_stub'
15 failed in 0.05s
*版本*
2.1
*指向路径*
/tests/test_agent_minimal_flow.py

# E03 - GREEN
*测试指令*
python -m pytest tests/test_agent_minimal_flow.py -q
*输出摘要*
FAILED tests/test_agent_minimal_flow.py::test_ready_context_calls_read_only_tool_once_and_finishes_enriched - ModuleNotFoundError: No module named 'app.services.agent_runtime'
FAILED tests/test_agent_minimal_flow.py::test_missing_required_context_input_stops_in_manual_without_calling_tool[missing-case-id] - ModuleNotFoundError: No module named 'app.services.agent_runtime'
FAILED tests/test_agent_minimal_flow.py::test_missing_required_context_input_stops_in_manual_without_calling_tool[missing-evidence-refs] - ModuleNotFoundError: No module named 'app.services.agent_runtime'
FAILED tests/test_agent_minimal_flow.py::test_missing_required_context_input_stops_in_manual_without_calling_tool[missing-correlation-id] - ModuleNotFoundError: No module named 'app.services.agent_runtime'
FAILED tests/test_agent_minimal_flow.py::test_missing_required_context_input_stops_in_manual_without_calling_tool[missing-case-id-and-evidence-refs] - ModuleNotFoundError: No module named 'app.services.agent_runtime'
FAILED tests/test_agent_minimal_flow.py::test_missing_required_context_input_stops_in_manual_without_calling_tool[missing-case-id-and-correlation-id] - ModuleNotFoundError: No module named 'app.services.agent_runtime'
FAILED tests/test_agent_minimal_flow.py::test_missing_required_context_input_stops_in_manual_without_calling_tool[missing-evidence-refs-and-correlation-id] - ModuleNotFoundError: No module named 'app.services.agent_runtime'
FAILED tests/test_agent_minimal_flow.py::test_missing_required_context_input_stops_in_manual_without_calling_tool[missing-all-context-inputs] - ModuleNotFoundError: No module named 'app.services.agent_runtime'
FAILED tests/test_agent_minimal_flow.py::test_tool_timeout_stops_in_manual_without_retry - ModuleNotFoundError: No module named 'app.services.agent_runtime'
FAILED tests/test_agent_minimal_flow.py::test_zero_budget_before_call_stops_in_manual_without_calling_tool - ModuleNotFoundError: No module named 'app.services.agent_runtime'
FAILED tests/test_agent_minimal_flow.py::test_second_tool_call_attempt_stops_in_manual_without_another_call - ModuleNotFoundError: No module named 'app.services.agent_runtime'
FAILED tests/test_agent_minimal_flow.py::test_non_entry_state_cannot_start_another_successful_run[restart-from-enriching] - ModuleNotFoundError: No module named 'app.services.agent_runtime'
FAILED tests/test_agent_minimal_flow.py::test_non_entry_state_cannot_start_another_successful_run[restart-from-enriched] - ModuleNotFoundError: No module named 'app.services.agent_runtime'
FAILED tests/test_agent_minimal_flow.py::test_non_entry_state_cannot_start_another_successful_run[restart-from-manual] - ModuleNotFoundError: No module named 'app.services.agent_runtime'
FAILED tests/test_agent_minimal_flow.py::test_success_trace_does_not_skip_enriching_state - ModuleNotFoundError: No module named 'app.services.agent_runtime'
15 failed in 0.11s
失败全部向 runtime 缺口推进
*指向路径*
/app/contracts/agent.py
/app/ports/tool_gateway.py
/app/adapters/read_only_tool_stub.py
/app/services/agent_runtime.py
/tests/test_agent_minimal_flow.py

# E04 - runtime + API
*测试指令*
python -m pytest tests/test_agent_minimal_flow.py -q
*输出摘要*
15 passed in 0.05s
*指向路径*
/app/services/agent_runtime.py
/app/api/agent_runs.py
/app/main.py
/tests/test_agent_minimal_flow.py

# E05 - 回归与证据
*D04 smoke测试指令*
python -m pytest tests/test_agent_minimal_flow.py -q
echo $?
*D04 smoke输出摘要*
15 passed in 0.05s
0
*运行全部回归指令*
python -m pytest -q
echo $?
*运行全部回归输出摘要*
25 passed, 1 warning in 0.17s
0
*API 启动检查指令*
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
*API 启动检查输出结果*
INFO:     Started server process [44686]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
*指向路径*
/tests/test_agent_minimal_flow.py
/tests/test_case_evidence_integration.py
/tests/test_investigation_intake.py
/tests/test_health.py

