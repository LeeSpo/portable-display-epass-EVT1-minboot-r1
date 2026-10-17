# KiCad 检查方式记录

2026-09-20 的 U1/U2 修复以保存后的主 PCB、KiCad 10.0.6 原生 CLI DRC、独立二维几何与连通审计为验收依据。最终结果为 0 未连接、0 违规、0 告警；报告见 `verification/drc.json` 及对应文件哈希。

曾尝试编辑器 Interactive Router 的 Shove 模式，但界面控制点击位置与实际选中对象不一致，因此没有采用或保存该尝试的交互布线修改。随后通过精确坐标调整局部线路，并由原生 DRC 验证。不能将此记录表述为已完成交互推挤布线或 GUI 手工签核。

四层预览与原生 SVG 已从最终主文件重新生成。2026-09-11 的旧窗口检查记录存放于本轮 `verification/u1u2_repair_20260919/before_promotion/`，不代表最新板文件。

当前状态以 `README_CN.md`、`FOOTPRINT_REVIEW_CN.md`、`OPEN_ISSUES_CN.md` 与哈希匹配的验证报告为准；仍未完成生产验收。
