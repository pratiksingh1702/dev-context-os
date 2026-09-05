#!/usr/bin/env bash
# Git Pre-Push Hook: Intercepts push and checks for active concurrent collisions

# Get list of files modified in this push compared to origin/main
CHANGED_FILES=$(git diff --name-only origin/main 2>/dev/null || git diff --name-only HEAD~1)

if [ -z "$CHANGED_FILES" ]; then
    exit 0
fi

# Run Context OS Conflict Interceptor
python -m hooks.interceptor $CHANGED_FILES
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "[Context OS] Push paused due to concurrent session collision."
    echo "To override and push anyway, run: git push --no-verify"
    exit 1
fi

exit 0
