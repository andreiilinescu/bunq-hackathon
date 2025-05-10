#!/bin/bash

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <branch> <commit-message>"
    exit 1
fi

BRANCH="$1"
COMMIT_MSG="$2"

CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

if [ "$CURRENT_BRANCH" != "$BRANCH" ]; then
    echo "Error: You are on branch '$CURRENT_BRANCH', but you specified '$BRANCH'."
    exit 1
fi

git add .
git commit -m "$COMMIT_MSG"
git push origin "$BRANCH"