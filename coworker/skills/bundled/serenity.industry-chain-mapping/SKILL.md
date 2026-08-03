---
name: serenity.industry-chain-mapping
description: 把一个主题拆成需求、系统、器件、工艺、设备材料和基础设施等层级。Map a theme across demand, systems, components, processes, equipment, materials, and infrastructure.
---
# 产业链层级测绘

当用户给出一个研究主题时，按以下层级拆解产业链：

1. **需求与应用** — 谁在什么场景下需要什么
2. **系统与产品** — 终端产品或系统形态
3. **器件与组件** — 关键子系统或功能模块
4. **工艺与制造** — 核心工艺路线
5. **设备与材料** — 专用设备、关键原材料
6. **基础设施** — 公用工程、物流、认证等支撑

输出要求：

- 每一层列出 3–7 个关键节点，注明与主题的关联
- 标注不确定之处，不臆造具体公司或产能数字
- 用户需要可视化时，可输出 fenced `mermaid` 流程图（自上而下层级图）

默认用简体中文回答；用户明确要求英文时切换。
