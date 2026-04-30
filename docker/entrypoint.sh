#!/bin/bash
set -euo pipefail

# ============================================================================
# entrypoint.sh — Docker entrypoint for wiki-to-pdf
#
# Environment variables (all optional, have defaults):
#   CONFIG_FILE      — path to mkdocs.yml               (default: /workspace/project/mkdocs.yml)
#   ATTACHMENTS_DIR  — extra assets dir to copy         (default: "")
#   OUTPUT_DIR       — directory for generated PDF      (default: /workspace/output)
#   OUTPUT_FILENAME  — PDF filename                     (default: document.pdf)
#   PDF_TITLE        — cover page title                 (default: "")
#   PDF_SUBTITLE     — cover page subtitle              (default: "")
#   PDF_AUTHOR       — author shown on cover            (default: "")
#   PDF_COPYRIGHT    — copyright line on cover          (default: "")
#   TOC_LEVEL        — table-of-contents depth 1-6      (default: "")
#   VERSION_TABLE    — path to YAML/JSON version table  (default: "")
#   VERSION_FROM_GIT — auto-generate from git tags/log  (default: "")
#   VERSION_EXCLUDE_PATTERN — regex to exclude commits  (default: "")
# ============================================================================

# Ensure native libs are discoverable in slim containers
export LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:/usr/lib/aarch64-linux-gnu:/usr/lib64:/usr/local/lib:${LD_LIBRARY_PATH:-}"

CONFIG_FILE="${CONFIG_FILE:-/workspace/project/mkdocs.yml}"
ATTACHMENTS_DIR="${ATTACHMENTS_DIR:-}"
OUTPUT_DIR="${OUTPUT_DIR:-/workspace/output}"
OUTPUT_FILENAME="${OUTPUT_FILENAME:-document.pdf}"

echo "============================================================"
echo " wiki-to-pdf  —  Docker build"
echo "============================================================"
echo " Config File    : ${CONFIG_FILE}"
echo " Output         : ${OUTPUT_DIR}/${OUTPUT_FILENAME}"
echo " Title          : ${PDF_TITLE:-<from mkdocs.yml>}"
echo " Subtitle       : ${PDF_SUBTITLE:-<from mkdocs.yml>}"
echo " Author         : ${PDF_AUTHOR:-<from mkdocs.yml>}"
echo " TOC level      : ${TOC_LEVEL:-<from mkdocs.yml>}"
echo " Version table  : ${VERSION_TABLE:-<none>}"
echo " Version git    : ${VERSION_FROM_GIT:-<disabled>}"
if [ -n "${ATTACHMENTS_DIR}" ]; then
echo " Attachments    : ${ATTACHMENTS_DIR}"
fi
echo "============================================================"

# ---- Validate input --------------------------------------------------------
if [ ! -f "${CONFIG_FILE}" ]; then
    echo "ERROR: Config file not found: ${CONFIG_FILE}" >&2
    echo "Please mount your project directory to /workspace/project" >&2
    exit 1
fi

# ---- Create output directory ------------------------------------------------
mkdir -p "${OUTPUT_DIR}"

# ---- Build the Python command -----------------------------------------------
CMD=(python3 /workspace/src/build_pdf.py)
CMD+=(--config "${CONFIG_FILE}")
CMD+=(--output "pdf/${OUTPUT_FILENAME}")

if [ -n "${ATTACHMENTS_DIR}" ]; then
    CMD+=(--attachments-dir "${ATTACHMENTS_DIR}")
fi

if [ -n "${PDF_TITLE:-}" ]; then
    CMD+=(--title "${PDF_TITLE}")
fi

if [ -n "${PDF_SUBTITLE:-}" ]; then
    CMD+=(--subtitle "${PDF_SUBTITLE}")
fi

if [ -n "${PDF_AUTHOR:-}" ]; then
    CMD+=(--author "${PDF_AUTHOR}")
fi

if [ -n "${PDF_COPYRIGHT:-}" ]; then
    CMD+=(--copyright "${PDF_COPYRIGHT}")
fi

if [ -n "${TOC_LEVEL:-}" ]; then
    CMD+=(--toc-level "${TOC_LEVEL}")
fi

if [ -n "${VERSION_TABLE:-}" ]; then
    CMD+=(--version-table "${VERSION_TABLE}")
fi

if [ -n "${VERSION_FROM_GIT:-}" ]; then
    CMD+=(--version-from-git)
fi

if [ -n "${VERSION_EXCLUDE_PATTERN:-}" ]; then
    CMD+=(--version-exclude-pattern "${VERSION_EXCLUDE_PATTERN}")
fi

# ---- Run the build script ---------------------------------------------------
"${CMD[@]}"

# ---- Copy PDF to output mount -----------------------------------------------
if [ -f "/workspace/pdf/${OUTPUT_FILENAME}" ]; then
    cp "/workspace/pdf/${OUTPUT_FILENAME}" "${OUTPUT_DIR}/${OUTPUT_FILENAME}"
    PDF_SIZE=$(du -h "${OUTPUT_DIR}/${OUTPUT_FILENAME}" | cut -f1)
    echo ""
    echo "============================================================"
    echo " PDF generated: ${OUTPUT_DIR}/${OUTPUT_FILENAME}  (${PDF_SIZE})"
    echo "============================================================"
else
    echo "ERROR: PDF was not generated" >&2
    exit 1
fi
