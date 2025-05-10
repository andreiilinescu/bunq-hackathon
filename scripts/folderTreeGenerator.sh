#!/bin/bash

# folderTreeGenerator.sh
# Usage: ./folderTreeGenerator.sh

# List of ignored patterns (folders/files)
IGNORED_PATTERNS=(
    ".git"
    "__pycache__"
    ".venv"
    "venv"
    ".mypy_cache"
    ".pytest_cache"
    ".idea"
    ".vscode"
    "build"
    "dist"
    "*.egg-info"
)

should_ignore() {
    local name="$1"
    for pattern in "${IGNORED_PATTERNS[@]}"; do
        if [[ "$name" == $pattern ]] || [[ "$name" == $pattern ]]; then
            return 0
        fi
        # For glob patterns
        if [[ "$pattern" == *"*"* ]] && [[ "$name" == $pattern ]]; then
            return 0
        fi
    done
    return 1
}

print_tree() {
    local dir="$1"
    local prefix="$2"
    local entries=()
    while IFS= read -r entry; do
        local basename=$(basename "$entry")
        should_ignore "$basename" && continue
        entries+=("$entry")
    done < <(find "$dir" -mindepth 1 -maxdepth 1 | sort)

    local count=${#entries[@]}
    for i in "${!entries[@]}"; do
        local basename=$(basename "${entries[$i]}")
        if [ "$i" -eq $((count - 1)) ]; then
            echo "${prefix}└── $basename"
            print_tree "${entries[$i]}" "${prefix}    "
        else
            echo "${prefix}├── $basename"
            print_tree "${entries[$i]}" "${prefix}│   "
        fi
    done
}

echo "."
print_tree "." ""