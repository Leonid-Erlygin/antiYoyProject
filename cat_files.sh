#!/usr/bin/env bash
set -euo pipefail

# ================= CONFIGURATION =================
OUTPUT_FILE="combined.txt"
TARGET_DIR="."
EXCLUDE_DIRS=("venv" ".git" "__pycache__" "/app/datasets" "/app/notebooks" "/app/training/optimizers" "configs/latex_tables" "outputs" "sandbox" "voxblink_data" "dist" "build" ".vscode")
# =================================================

if [[ ! -d "$TARGET_DIR" ]]; then
    echo "❌ Error: Directory '$TARGET_DIR' does not exist."
    exit 1
fi

# Build prune conditions for find (handles both names & absolute paths)
prune_args=()
first=true
for dir in "${EXCLUDE_DIRS[@]}"; do
    # Strip leading / if present so -path works consistently from any TARGET_DIR
    clean_dir="${dir#/}"
    if $first; then
        prune_args+=(-path "*/$clean_dir" -type d)
        first=false
    else
        prune_args+=(-o -path "*/$clean_dir" -type d)
    fi
done

# Construct the find command
if [ ${#prune_args[@]} -eq 0 ]; then
    find_cmd=(find "$TARGET_DIR" -type f \( -name "*.py" -o -name "*.yaml" -o -name "*.md" \) -print0)
else
    find_cmd=(find "$TARGET_DIR" \( "${prune_args[@]}" \) -prune -o -type f \( -name "*.py" -o -name "*.yaml" -o -name "*.md" \) -print0)
fi

# Clear output file
> "$OUTPUT_FILE"

echo "🚀 Starting scan in: $TARGET_DIR"
echo "📁 Excluding: ${EXCLUDE_DIRS[*]}"
echo "📄 Output: $OUTPUT_FILE"
echo "--------------------------------------------------"

prev_dir=""
file_count=0

# Process files. `sort -z` groups files by directory for cleaner progress output.
# Remove `| sort -z` if you prefer raw filesystem traversal order.
while IFS= read -r -d '' file; do
    current_dir=$(dirname "$file")
    if [[ "$current_dir" != "$prev_dir" ]]; then
        echo "📂 Scanning: $current_dir"
        prev_dir="$current_dir"
    fi

    printf "\n# === %s ===\n\n" "$file" >> "$OUTPUT_FILE"
    cat "$file" >> "$OUTPUT_FILE"
    file_count=$((file_count + 1))
done < <("${find_cmd[@]}" | sort -z 2>/dev/null)

echo "--------------------------------------------------"
echo "✅ Done! Concatenated $file_count files into $OUTPUT_FILE"