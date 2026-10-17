#!/usr/bin/env bash
# =============================================================================
# export_gerber.sh — 使用 kicad-cli 导出 Gerber 文件并打包 ZIP
# =============================================================================
# 用法:
#   ./tools/export_gerber.sh [PCB_FILE] [OUTPUT_DIR]
#
# 默认值:
#   PCB_FILE   = split-power-candidate/ak_display_38x64_SPLIT_POWER_CANDIDATE.kicad_pcb
#   OUTPUT_DIR = gerber_output/
# =============================================================================

set -euo pipefail

# --- 配置 -------------------------------------------------------------------
KICAD_CLI="/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

PCB_FILE="${1:-${WORKSPACE_DIR}/split-power-candidate/ak_display_38x64_SPLIT_POWER_CANDIDATE.kicad_pcb}"
OUTPUT_BASE="${2:-${WORKSPACE_DIR}/gerber_output}"

# 从 PCB 文件名提取板名
BOARD_NAME="$(basename "${PCB_FILE}" .kicad_pcb)"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
GERBER_DIR="${OUTPUT_BASE}/${BOARD_NAME}_gerber"
ZIP_FILE="${OUTPUT_BASE}/${BOARD_NAME}_${TIMESTAMP}.zip"

# 4层板 Gerber 层定义
GERBER_LAYERS="F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts,F.Fab,B.Fab"

# --- 前置检查 ---------------------------------------------------------------
echo "╔══════════════════════════════════════════════════════╗"
echo "║           KiCad Gerber 导出脚本 v1.0                 ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

if [[ ! -f "${KICAD_CLI}" ]]; then
    echo "❌ 错误: 找不到 kicad-cli: ${KICAD_CLI}"
    exit 1
fi

if [[ ! -f "${PCB_FILE}" ]]; then
    echo "❌ 错误: 找不到 PCB 文件: ${PCB_FILE}"
    exit 1
fi

echo "📋 板文件  : ${PCB_FILE}"
echo "📁 输出目录: ${GERBER_DIR}"
echo "📦 ZIP 文件: ${ZIP_FILE}"
echo ""

# --- 创建输出目录 -----------------------------------------------------------
rm -rf "${GERBER_DIR}"
mkdir -p "${GERBER_DIR}"
mkdir -p "${OUTPUT_BASE}"

# --- 1. 导出 Gerber 文件 ---------------------------------------------------
echo "▶ [1/3] 导出 Gerber 文件..."
"${KICAD_CLI}" pcb export gerbers \
    --output "${GERBER_DIR}" \
    --layers "${GERBER_LAYERS}" \
    --precision 6 \
    --no-x2 \
    --no-netlist \
    --use-drill-file-origin \
    "${PCB_FILE}"

echo "   ✅ Gerber 导出完成"

# --- 2. 导出钻孔文件 -------------------------------------------------------
echo "▶ [2/3] 导出钻孔文件 (Excellon)..."
"${KICAD_CLI}" pcb export drill \
    --output "${GERBER_DIR}/" \
    --format excellon \
    --drill-origin absolute \
    --excellon-zeros-format decimal \
    --excellon-units mm \
    --excellon-separate-th \
    --generate-map \
    --map-format gerberx2 \
    "${PCB_FILE}"

echo "   ✅ 钻孔文件导出完成"

# --- 3. 打包 ZIP -----------------------------------------------------------
echo "▶ [3/3] 打包 ZIP..."
cd "${GERBER_DIR}" && zip -r "${ZIP_FILE}" . -x "*.DS_Store"
cd "${WORKSPACE_DIR}"

echo "   ✅ ZIP 打包完成"
echo ""

# --- 输出文件清单 -----------------------------------------------------------
echo "════════════════════════════════════════════════════════"
echo "📦 ZIP 文件已生成："
echo "   ${ZIP_FILE}"
echo ""
echo "📄 Gerber 文件列表："
ls -lh "${GERBER_DIR}" | tail -n +2 | awk '{printf "   %-40s %s\n", $9, $5}'
echo ""
echo "📊 ZIP 大小: $(du -sh "${ZIP_FILE}" | cut -f1)"
echo "════════════════════════════════════════════════════════"
echo "✅ 所有操作完成！"
