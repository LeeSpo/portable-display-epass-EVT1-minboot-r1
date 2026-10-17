# KiCad 窗口续作检查

本轮未完成布线优化，不能投板。

尝试将 L2、C6、C7 向右移动 0.5 mm，为 U1 核心反馈留出空间。原生 DRC 检出 L2 与 VSYS 走线、C7 与 CORE 走线合计 3 项短路；试摆及试加过孔均已撤回。重新铺铜、保存并运行原生 DRC 后，恢复为 19 处未连接、131 项违规/告警，没有 shorting_items 或 clearance 项。

编辑器坐标选取与实际选中对象未能可靠对应，本轮未继续进行精细布线，避免误改。U1/U2 CORE、电源地孤岛、SD/控制信号、热连接及高速检查仍需完成。

本次保存版本对应 verification/gui_followup_drc.json 和 gui_followup_provenance.json。此前报告和四层预览属于此前版本，不能替代本次检查。
