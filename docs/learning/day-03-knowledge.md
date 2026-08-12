# K01
*如何按 id 读取既有 investigation*
告警接收的investigation保存在idempotency_store的字典中，而 investigation_id 位于每条记录的首次响应里
在app/services/idempotency.py 中增加了一个只读查询方法
它遍历所有记录，找到后返回完整响应的深拷贝；找不到返回 None。业务服务必须先执行该查询，未知 ID 在调用 Stub 前停止。
*correlation_id 从哪里来？*
它来自既有investigation的首次告警接收响应。
创建investigation时，如果请求带有 X-Correlation-ID，D02 保存该值；
如果没有提供，D02 生成 corr_...。
这是告警接收业务中安全重放复用首次保存的值。
今天的查询上下文业务从只读查询结果的 investigation["correlation_id"] 取出correlation_id，成功和 503 原样传递该值，不能重新生成。未知 ID 没有既有 investigation，因此不能生成 correlation_id
*四个冻结对象*
| Contract | 冻结字段 |
| `CaseBinding` | `case_id`、`investigation_id`、`status="open"` |
| `EvidenceRef` | `evidence_id`、`source_type="synthetic_alert"`、`source_id`、`captured_at`、`content_hash` |
| `ContextResult` | `status="CONTEXT_READY"`、`investigation_id`、`case_id`、`evidence_refs`、`correlation_id` |
| `DependencyError` | `error_code="CASE_EVIDENCE_UNAVAILABLE"`、`message`、`correlation_id` |

# K02 - 先写三条会失败的测试
写三个测试场景：
- 场景一（成功）：拿一个真实存在的调查任务 ID 去查，系统应该返回包含 case_id、evidence_refs 和 CONTEXT_READY 的成功数据，并且必须带上原来保存的 correlation_id
- 场景二（404 找不到）：拿一个根本不存在的 ID 去查，系统应该返回 404，并且绝对不能凭空捏造任何 correlation_id、case_id 或 evidence_refs
- 场景三（503 依赖挂了）：拿一个真实存在的 ID 去查，但是假装背后的查案系统（Stub）坏了，系统应该返回 503 错误，保留原来的 correlation_id，但不能捏造案件号或证据

# K03 - 按规定字段实现 Contract、Port 和确定性 Stub
这一步先定义好数据的契约（Contract），再定义交互的规矩（Port），最后用假数据（Stub）把规矩实现了
1. 实现 Contract（数据契约）— app/contracts/case_evidence.py
定义数据结构，告诉系统：团队那边传过来的数据长什么样（CaseBinding、EvidenceRef），我们返回的数据长什么样（ContextResult 、 DependencyError）
2. 实现 Port（接口）— app/ports/case_evidence.py
定义消费这些对象所需的最小读取接口
3. 实现 Stub（教学替身）— app/adapters/case_evidence_stub.py
这是一个模拟器，它实现了上面的 CaseEvidencePort 接口，它有一个开关 mode，如果是 available，它就返回任务书里写死的假数据（inv-demo-001/...）；如果是 unavailable，它就抛出一个约定好的503错误。

# K04 - 组装
把之前写好的契约（Contract）、规矩（Port）和准备好的假数据（Stub）组装起来，让API能跑通
1. 实现了业务服务 — context_preparation.py
创建了一个新的服务文件 app/services/context_preparation.py，负责处理整个业务流程，具体工作流程是：
收到请求后，它首先会去 idempotency.py 里查询这个 investigation_id 是否存在。如果 ID 不存在，它会立刻返回 404 错误，且不会去调用后面的 Stub；当 ID 存在时，才会调用 case_evidence_port（Stub）。
如果 Stub 返回成功，它会把拿到的 case_id 和 evidence_refs 保存下来；如果 Stub 返回失败，它会报告错误，并且不会伪造或保存任何 case 或 evidence 信息。
2. 实现了 API 路由 — investigation_context.py
创建了 app/api/investigation_context.py，它负责处理HTTP请求和响应，它根据业务服务的指令，返回三种结果：
- 成功 (200 OK)：返回一个包含 status='CONTEXT_READY'、case_id、evidence_refs 和从旧调查中读取的 correlation_id 的完整响应
- 调查不存在 (404 Not Found)：当 investigation_id 找不到时，它会返回 404 错误，这个响应里不会包含 correlation_id、case_id 或 evidence_refs
- 依赖不可用 (503 Service Unavailable)：当 Stub 模拟故障时，它会返回 503 错误和固定的 error_code，会保留并返回那个已存在的 correlation_id，但不会包含case和evidence
3. 完成了最后的连接  — idempotency.py 和 main.py
在idempotency.py里增加了一个只读查询方法，只负责根据ID查找并返回已有的调查信息
在 main.py 中把新写的API路由注册进去，增加新接口

# K05 - 运行测试
*1. 运行聚焦测试*
运行针对新功能编写的测试，会专门检查刚刚实现的“成功”、“404 找不到”和“503 依赖挂了”这三个场景，看到全部 PASSED，就证明新功能本身是工作的
*2. 运行全量回归测试*
一口气运行健康检查、告警接入和上下文绑定的所有测试，证明了系统整体是健康的

# 问题
*为什么 Contract、Port、Adapter Stub 不应混在 API 路由里？*
因为API路由的职责仅是把 HTTP请求翻译成内部调用，再把内部结果翻译成HTTP 状态码。
如果把 Contract、Port和 Stub都塞进路由里，路由就会很臃肿。
*团队 Case/Evidence Stub 不可用时，为什么 503 响应不能带出新的 `case_id` 或 `evidence_refs`？*
当Stub不可用时意味着外部查案服务挂了，系统根本没有获取到任何案件或证据信息。如果此时返回了 case_id 或 evidence_refs，那必然是系统伪造的
*怎样用测试分别证明：成功与 503 保留既有 investigation 已保存的 `correlation_id`，而未知 id 的 404 不生成 `correlation_id`？*
- 对于成功和503：在测试的准备阶段生成一个固定的correlation_id并写入内存数据库。发请求后，在断言阶段使用 assert payload["correlation_id"] == saved_correlation_id。只要绿灯亮起，就证明系统忠实地透传了既有ID。
- 对于未知404：在断言阶段使用 assert "correlation_id" not in payload。只要绿灯亮起，就证明系统在遇到未知 ID 时拒绝了请求，没有越权生成追踪标识
*请用“输入、输出、负责什么、不负责什么”分别说明 Contract、Port、Adapter 和 Stub 的职责，它们为什么不能全部写进 API 路由？*
- Contract
无输入，输出数据结构定义、里面有哪些字段，字段的固定值等等。
契约负责定义数据的绝对形状和固定值，不负责数据的获取、存储或业务流转
- Port
输入的是investigation_id 和 correlation_id，输出成功的数据组合或冻结的错误对象
负责定义业务层与外部服务交互的最小实现的规矩，不负责网络请求
- Adapter
输入符合Port定义的参数（investigation_id, correlation_id），输出符合Contract契约的数据对象，或真实网络异常转换后的冻结错误对象。
Adapter负责发起HTTP请求、数据库查询、将外部系统返回的原始数据解析并映射为内部严格定义的 Contract对象，此外，捕获异常将其转换为冻结错误。不负责数据的处理和保存，也不负责HTTP 响应
- Stub
输入与符合Port定义的参数（investigation_id, correlation_id），输出写死的假数据（Fixture），或根据开关状态返回冻结的错误对象。
Stub负责通过控制mode="available" 或 mode="unavailable"模拟外部服务正常或崩溃的场景，此外它只返回任务书规定的固定假数据（如case-demo-001），确保自动化测试可以重复测试。
不负责真实数据的获取
- 为什么不能全部写进 API 路由？
路由会失去通用性，只能针对教学假数据和特定的HTTP协议来工作，未来如果要修改，就得把整个路由推倒重写。拆分它们，是为了让每一层只做一件事，且未来可以独立替换。
*Stub 不可用时，为什么 503 响应不能返回新的 case_id 或 evidence_refs？如果返回了，这会让调用方误以为什么？*
503代表依赖服务不可用，如果返回了新的 case_id 或 evidence_refs，调用方会误以为查案服务是正常的，并且会拿着伪造的ID去进行下一步，这是错误的
*为什么成功路径和 503 都要保留既有 investigation 已保存的 correlation_id，而未知 ID 的 404 不能临时生成 correlation_id？*
- 成功和503保留correlation_id：因为这两种情况都证明所查的Investigation确实存在。保留 correlation_id 是为了追踪。假如说下游服务挂了（503），可以通过这个correlation_id在日志中定位排查问题
- 未知404不生成correlation_id：因为系统不认识这个 ID。如果系统为不存在的ID生成了correlation_id，这就是系统对非法/越权请求做出了过度响应