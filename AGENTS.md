## 完整流程
请按 OpenSpec + Superpowers 三段式流程执行这个需求：先用 Superpowers 做探索性规划，再用 OpenSpec 锁定 proposal/design/spec/tasks，最后回到 Superpowers 执行编码、测试、验证和归档。

## 只做探索阶段
先不要写 OpenSpec，也不要写代码。请先用 Superpowers 做需求探索、方案比较和设计确认。

## 进入 OpenSpec 阶段
设计已经确认。请基于当前设计创建 OpenSpec change，并补齐 proposal、design、spec 和 tasks。完成后先暂停，不要开始编码。

## 进入执行阶段
OpenSpec 已确认。请回到 Superpowers 执行阶段：写实现计划，使用 worktree，按 TDD 实现，并运行真实验证命令。

## 进入归档阶段
请确认代码、测试和 OpenSpec 规范已经对齐。如果验证通过，请归档这个 OpenSpec change。





## OpenSpec + Superpowers 工作流
1. Superpowers 探索性规划
2. OpenSpec 锁定规范
3. Superpowers 执行编码、测试、验证
4. OpenSpec 归档

## 强制规则
- 设计未确认前，不进入 OpenSpec。
- OpenSpec artifacts 未完成前，不进入编码。
- 行为变更默认使用 TDD。
- 完成前必须运行真实验证命令。
- 代码、测试、规范未对齐前，不归档。


## Review 检查清单
是否完成 Superpowers 探索？ 
否有设计草稿？ 
是否创建 OpenSpec change？ 
是否有 proposal.md？ 
否有 design.md？ 
是否有 spec.md？ 
是否有 tasks.md？ 
是否写了实现计划？ 
是否补充测试？ 
是否运行真实验证命令？ 
tasks.md 是否全部完成？ 
代码、测试、规范是否一致？ 
是否完成 OpenSpec 归档？