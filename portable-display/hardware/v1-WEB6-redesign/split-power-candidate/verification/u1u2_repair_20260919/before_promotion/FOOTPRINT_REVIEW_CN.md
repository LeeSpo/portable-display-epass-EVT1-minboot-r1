# 指定器件封装核查与修正记录

核查日期：2026-09-10 至 2026-09-11。已先核对厂家资料，再修改候选 PCB 和本目录 `sameat.pretty`。数据手册的封装底视图已转换为 PCB 顶视图；引脚网络保持既定映射。

| 器件 | 核查结论 | 当前处理 |
|---|---|---|
| U2 V851S | 88 个外围脚与全志 pinout 表逐项一致；PCB 的 89 号为接地 EPAD。封装本体为 9×9 mm、0.35 mm pitch。 | F.Fab 改为 9×9 mm；原 5.2×5.2 mm EP 与外围铜焊盘暂保留，尚未取得厂家推荐 PCB land。 |
| U1 AXP2101 | 1～40 的功能编号对应；本体 5×5 mm、0.4 mm pitch。 | F.Fab 改为 5×5 mm；原 3.1×3.1 mm EP 与外围铜焊盘暂保留，推荐 PCB land 尚未确认。 |
| U4 LIS2DW12 | **原排列错误，不能仅归为 Fab 偏大。** 官方为四边 4、2、4、2 个端子；原库为每边 3 个。 | 改为 4-2-4-2，0.5 mm pitch，本体 2×2 mm。按 ST 安装指南配置焊盘、阻焊及局部禁止布线/过孔区域，恢复供电、I²C 与中断连接。 |
| U5 RV-3028-C7 | **原排列错误。** 应为两排横向焊盘，0.9 mm pitch；原为左右两列、0.5 mm pitch。 | 重建为本体 3.2×1.5 mm、焊盘 0.5×0.8 mm、两排中心距 1.2 mm，并恢复全部相关连接。 |
| U6 SN74LVC1G123DCTR | 引脚功能和 0.65 mm pitch 对应 DCT8。原焊盘接近可用尺寸，但与本次查到的 TI 推荐图不同。 | 使用专用 DCT8 封装：焊盘 1.1×0.4 mm，两列中心距 3.8 mm，本体 3×3 mm。 |
| U8 TPS22918DBVR | 引脚功能和 0.95 mm pitch 正确；原通用焊盘偏短。 | 使用专用 DBV6 封装：焊盘 1.1×0.6 mm，两列中心距 2.6 mm。 |
| U9 USBLC6-2SC6 | 引脚功能和 0.95 mm pitch 正确；原通用焊盘与 ST 推荐不同。 | 使用专用封装：焊盘 1.2×0.6 mm，两列中心距 **2.3 mm**，不是 2.9 mm。 |

修正后的封装保存在工程本地库，PCB 内嵌封装与该库同步。已补充相应 F.Fab 1 脚标记。库一致性通过不等于全部 119 个器件均已通过厂家封装审核；本次厂家核查范围为表内 7 个 IC。

## U4 与 U5 的坐标依据

以下为封装局部坐标，单位 mm，PCB 顶视图，X 向右、Y 向下。

- U4：1～4 位于 X=-0.7625，Y=-0.75/-0.25/0.25/0.75；5、6 位于 Y=0.7625，X=-0.25/0.25；7～10 位于 X=0.7625，Y=0.75/0.25/-0.25/-0.75；11、12 位于 Y=-0.7625，X=0.25/-0.25。左右侧焊盘为 0.375×0.35，上下侧为 0.35×0.375。
- U4 的尺寸结合 DS11811 Rev 9 机械端子和 TN0018 Rev 8 §3.7 的焊盘余量制定；不是把数据手册中的底视图原样复制到 PCB。供电/地通过走线接入，器件中心禁止顶层走线，器件下方禁止过孔与顶层铺铜。
- U5：1～4 位于 Y=0.6，X=-1.35/-0.45/0.45/1.35；8、7、6、5 位于 Y=-0.6，同样从左到右排列。1 脚在左下角。

## U1、U2 仍需确认的内容

厂家图纸给出的裸露金属尺寸并不自动等于推荐 PCB 焊盘尺寸。U2 的芯片 EP 约 6.5×6.5 mm、U1 约 3.4×3.4 mm，而本板 PCB EP 分别为 5.2×5.2 和 3.1×3.1 mm，尚不能据此判定合格。外围焊盘与本体的覆盖关系也需随推荐 land 一并审核。

本次仅修正有明确依据的本体轮廓，没有把 EP 直接放大。若确认需要扩大 EP，必须重新检查中心区域扇出、阻焊、钢网开窗及散热过孔，不能只改一个尺寸后投板。

## 原始依据

- [Micro Crystal RV-3028-C7 数据手册](https://www.microcrystal.com/fileadmin/Media/Products/RTC/Datasheet/RV-3028-C7.pdf)，v1.3，2021-09，第 1～2 页，封装、引脚与推荐 land pattern。
- [ST LIS2DW12 数据手册](https://www.st.com/resource/en/datasheet/lis2dw12.pdf)，DS11811 Rev 9，第 4 页引脚底视图、第 56 页机械图。本次实际读取用户提供的 `/Users/spotible/Desktop/pdf/lis2dw12.pdf`。
- [ST TN0018 安装指南](https://www.st.com/resource/en/technical_note/tn0018-surface-mounting-guidelines-for-mems-sensors--in-an-lga-package--stmicroelectronics.pdf)，Rev 8，§3.7～3.9。
- [TI SN74LVC1G123](https://www.ti.com/lit/ds/symlink/sn74lvc1g123.pdf)，DCT0008A，4220784/D，2025-10；本次 PDF 第 23～24 页。
- [TI TPS22918](https://www.ti.com/lit/ds/symlink/tps22918.pdf)，DBV0006A，4214840/G，2024-08；本次 PDF 第 28 页。
- [ST USBLC6-2](https://www.st.com/resource/en/datasheet/usblc6-2.pdf)，DS4260 Rev 7，第 12～13 页，Figure 19。
- [全志社区提供的 AXP2101 厂家数据手册](https://bbs.aw-ol.com/assets/uploads/files/1662612785463-c9f5c599-8055-43f4-ae16-690bbc0536e6-axp2101_datasheet_v1.0_en.pdf)，V1.0，第 7～9 页引脚、第 59 页机械图。
- [全志社区提供的 V851S/V851SE 厂家数据手册](https://bbs.aw-ol.com/assets/uploads/files/1664112156052-c55b9458-9847-4731-873e-c98d352589ea-v851s-amp-v851se_datasheet_v0.1.pdf)，本次合并 PDF 第 36 页（页内编号 22）。
- [全志 V851S Pinout V0.1](https://bbs.aw-ol.com/assets/uploads/files/1664634614433-705eb7fa-ac80-4aa7-a263-45ee8d799341-v851s_pinout_v0.1.xlsx)，`1 Pin Characteristics` 工作表；逐脚结果见 `verification/routing_20260910/u2_pin_audit.json`。

以上结论不能替代剩余高速信号、装联工艺与机械验收。当前整体状态见 [未完成项](OPEN_ISSUES_CN.md)。
