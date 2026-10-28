#!/bin/bash

# Get the current branch name from the submodule
get_submodule_branch() {
    cd app/shared_db
    local branch=$(git rev-parse --abbrev-ref HEAD)
    cd ../..
    echo $branch
}

# Switch branches
if [ -n "$1" ]; then
    # Checkout the branch in main repo
    git checkout $1

    # Update submodule
    git submodule update --init

    # If it's one of the main branches, ensure submodule follows
    if [ "$1" = "development" ] || [ "$1" = "staging" ] || [ "$1" = "main" ]; then
        cd app/shared_db
        git checkout $1
        git pull origin $1  # Pull latest changes for the branch
        cd ../..
        git submodule update --remote  # Update submodule to latest remote version
    else
        # For feature branches, let developer know current submodule branch
        echo "Submodule 'app/shared_db' is on branch: $(get_submodule_branch)"
        echo "To switch submodule branch, cd into app/shared_db and use git checkout and git pull"
    fi
else
    echo "Usage: ./switch-branch.sh <branch-name>"
    echo "For main branches (development, staging, main), both repos will switch and update"
    echo "For feature branches, submodule branch remains unchanged"
    exit 1
fi
