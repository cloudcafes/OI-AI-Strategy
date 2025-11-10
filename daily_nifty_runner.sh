#!/bin/bash

# daily_nifty_runner.sh
# Script to run nifty_main.py daily at 5PM with git operations

# Configuration
SCRIPT_DIR="/root/OI-AI-Strategy"
MAIN_SCRIPT="nifty_main.py"
LOG_FILE="/root/OI-AI-Strategy/daily_runner.log"
GIT_REPO_DIR="/root/OI-AI-Strategy"
GIT_BRANCH="win-version"

# Function to log messages with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Function to check if we can push without authentication
can_push_without_auth() {
    log_message "Checking if push can be done without authentication..."
    
    cd "$GIT_REPO_DIR" || return 1
    
    # Try a dry-run push to check authentication
    push_check=$(timeout 15 git push --dry-run 2>&1)
    
    if echo "$push_check" | grep -q "fatal: Authentication failed"; then
        log_message "Authentication required for push"
        return 1
    elif echo "$push_check" | grep -q "fatal: could not read Username"; then
        log_message "Username prompt detected"
        return 1
    else
        log_message "Push appears to be possible without authentication"
        return 0
    fi
}

# Function to setup git authentication
setup_git_auth() {
    log_message "Setting up git authentication..."
    
    # Check if we're using SSH
    cd "$GIT_REPO_DIR" || return 1
    remote_url=$(git remote get-url origin)
    
    if echo "$remote_url" | grep -q "^git@"; then
        log_message "SSH remote detected, testing connection..."
        ssh -o BatchMode=yes -T git@github.com 2>&1 | grep -q "successfully authenticated"
        if [ $? -eq 0 ]; then
            log_message "SSH authentication is working"
            return 0
        else
            log_message "SSH authentication failed"
            return 1
        fi
    else
        log_message "HTTPS remote detected, credential helper will be used"
        return 0
    fi
}

# Function to setup git configuration
setup_git_config() {
    log_message "Setting up git configuration..."
    
    cd "$GIT_REPO_DIR" || {
        log_message "ERROR: Cannot change to repo directory $GIT_REPO_DIR"
        return 1
    }
    
    # Set pull strategy to merge (avoid divergent branch prompts)
    git config pull.rebase false >> "$LOG_FILE" 2>&1
    git config pull.ff only >> "$LOG_FILE" 2>&1
    
    # Set credential helper to store permanently
    git config credential.helper 'store' >> "$LOG_FILE" 2>&1
    
    log_message "Git configuration updated"
    return 0
}

# Function to switch to win-version branch
switch_to_win_version() {
    log_message "Switching to $GIT_BRANCH branch..."
    
    cd "$GIT_REPO_DIR" || {
        log_message "ERROR: Cannot change to repo directory $GIT_REPO_DIR"
        return 1
    }
    
    # Check current branch
    current_branch=$(git branch --show-current 2>/dev/null)
    log_message "Current branch: $current_branch"
    
    # Switch to win-version branch
    switch_output=$(git checkout "$GIT_BRANCH" 2>&1)
    switch_status=$?
    
    echo "$switch_output" >> "$LOG_FILE"
    
    if [ $switch_status -eq 0 ]; then
        log_message "Successfully switched to $GIT_BRANCH branch"
        return 0
    else
        log_message "ERROR: Failed to switch to $GIT_BRANCH branch - $switch_output"
        return 1
    fi
}

# Function to clean up temporary files that should not be in git
clean_temporary_files() {
    log_message "Cleaning up temporary files..."
    
    cd "$GIT_REPO_DIR" || {
        log_message "ERROR: Cannot change to repo directory $GIT_REPO_DIR"
        return 1
    }
    
    # Remove all __pycache__ directories
    if [ -d "__pycache__" ]; then
        log_message "Removing __pycache__ directory"
        rm -rf __pycache__
    fi
    
    # Remove any other .pyc files
    find . -name "*.pyc" -type f -delete >> "$LOG_FILE" 2>&1
    find . -name "*.pyo" -type f -delete >> "$LOG_FILE" 2>&1
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    
    log_message "Temporary files cleaned up"
    return 0
}

# Function to handle divergent branches by forcing local to match remote
handle_divergent_branches() {
    log_message "Handling divergent branches by resetting to remote..."
    
    # Clean up temporary files first
    clean_temporary_files
    
    # Fetch the latest from remote
    git fetch origin >> "$LOG_FILE" 2>&1
    
    # Reset local branch to match remote (force update)
    reset_output=$(git reset --hard "origin/$GIT_BRANCH" 2>&1)
    reset_status=$?
    
    echo "$reset_output" >> "$LOG_FILE"
    
    if [ $reset_status -eq 0 ]; then
        log_message "Successfully reset local branch to match remote"
        return 0
    else
        log_message "ERROR: Failed to reset branch - $reset_output"
        return 1
    fi
}

# Function to perform aggressive cleanup and fresh pull
aggressive_git_pull() {
    log_message "Performing aggressive git pull..."
    
    # Clean all temporary files
    clean_temporary_files
    
    # Stash any remaining changes
    git stash >> "$LOG_FILE" 2>&1
    
    # Reset to remote
    if handle_divergent_branches; then
        log_message "Aggressive git pull completed successfully"
        return 0
    else
        log_message "ERROR: Aggressive git pull failed"
        return 1
    fi
}

# Function to perform git pull with conflict resolution
safe_git_pull() {
    log_message "Performing git pull on $GIT_BRANCH branch..."
    
    cd "$GIT_REPO_DIR" || {
        log_message "ERROR: Cannot change to repo directory $GIT_REPO_DIR"
        return 1
    }
    
    # Ensure we're on the correct branch
    if ! switch_to_win_version; then
        return 1
    fi
    
    # Clean temporary files before pull
    clean_temporary_files
    
    # Stash any local changes first
    log_message "Stashing local changes..."
    git stash >> "$LOG_FILE" 2>&1
    
    # Try git pull with different strategies
    log_message "Attempting git pull..."
    pull_output=$(timeout 30 git pull --no-rebase 2>&1)
    pull_status=$?
    
    echo "$pull_output" >> "$LOG_FILE"
    
    # Check for timeout
    if [ $pull_status -eq 124 ]; then
        log_message "Git pull timed out, using aggressive approach..."
        if aggressive_git_pull; then
            return 0
        else
            return 1
        fi
    fi
    
    # Check for specific error conditions
    if echo "$pull_output" | grep -q "divergent branches"; then
        log_message "Divergent branches detected, handling..."
        if handle_divergent_branches; then
            log_message "Git pull completed after handling divergent branches"
            return 0
        else
            log_message "ERROR: Failed to handle divergent branches"
            return 1
        fi
    elif [ $pull_status -ne 0 ]; then
        log_message "Git pull encountered issues, trying aggressive approach..."
        if aggressive_git_pull; then
            return 0
        else
            log_message "ERROR: All git pull attempts failed"
            return 1
        fi
    fi
    
    log_message "Git pull completed successfully on $GIT_BRANCH branch"
    return 0
}

# Function to perform git push with authentication handling
safe_git_push() {
    log_message "Performing git push to $GIT_BRANCH branch..."
    
    cd "$GIT_REPO_DIR" || {
        log_message "ERROR: Cannot change to repo directory $GIT_REPO_DIR"
        return 1
    }
    
    # Ensure we're on the correct branch
    if ! switch_to_win_version; then
        return 1
    fi
    
    # Clean temporary files before push
    clean_temporary_files
    
    # Check if we can push without authentication issues
    if ! can_push_without_auth; then
        log_message "Cannot push due to authentication issues. Setting up authentication..."
        if ! setup_git_auth; then
            log_message "ERROR: Authentication setup failed. Cannot push."
            log_message "To fix this, run manually:"
            log_message "1. Generate SSH key: ssh-keygen -t ed25519 -C 'github@$(hostname)'"
            log_message "2. Add to GitHub: cat ~/.ssh/id_ed25519.pub"
            log_message "3. Change remote: git remote set-url origin git@github.com:cloudcafes/OI-AI-Strategy.git"
            return 1
        fi
    fi
    
    # Check if there are any changes to push
    if git diff --quiet && git diff --staged --quiet; then
        log_message "No changes to push"
        return 0
    fi
    
    # Add all changes (but exclude temporary files)
    git add . >> "$LOG_FILE" 2>&1
    
    # Remove any temporary files that might have been added
    git reset -- '__pycache__/' '*.pyc' '*.pyo' '.DS_Store' 2>/dev/null || true
    
    # Check if there are still changes after excluding temp files
    if git diff --quiet && git diff --staged --quiet; then
        log_message "No meaningful changes to push (only temporary files)"
        return 0
    fi
    
    # Commit changes
    commit_message="Automated commit - $(date '+%Y-%m-%d %H:%M:%S') - Daily nifty analysis"
    git commit -m "$commit_message" >> "$LOG_FILE" 2>&1
    
    # Push changes to win-version branch
    log_message "Pushing changes to $GIT_BRANCH branch..."
    push_output=$(timeout 30 git push origin "$GIT_BRANCH" 2>&1)
    push_status=$?
    
    echo "$push_output" >> "$LOG_FILE"
    
    if [ $push_status -eq 0 ]; then
        log_message "Git push to $GIT_BRANCH branch completed successfully"
        return 0
    else
        log_message "WARNING: Git push to $GIT_BRANCH branch failed - $push_output"
        log_message "Authentication setup required for automated pushes"
        return 1
    fi
}

# Function to run the main nifty script
run_nifty_script() {
    log_message "Starting nifty_main.py execution..."
    
    cd "$SCRIPT_DIR" || {
        log_message "ERROR: Cannot change to script directory $SCRIPT_DIR"
        return 1
    }
    
    # Ensure we're on the correct branch
    if ! switch_to_win_version; then
        return 1
    fi
    
    # Check if script exists
    if [ ! -f "$MAIN_SCRIPT" ]; then
        log_message "ERROR: Main script $MAIN_SCRIPT not found"
        return 1
    fi
    
    # Run the script
    log_message "Executing: python3 $MAIN_SCRIPT"
    
    # Run with timeout of 1 hour (3600 seconds) to prevent hanging
    timeout 3600 python3 "$MAIN_SCRIPT" >> "$LOG_FILE" 2>&1
    script_status=$?
    
    if [ $script_status -eq 0 ]; then
        log_message "nifty_main.py completed successfully"
    elif [ $script_status -eq 124 ]; then
        log_message "WARNING: nifty_main.py was terminated due to timeout (1 hour)"
    else
        log_message "WARNING: nifty_main.py exited with status $script_status"
    fi
    
    return $script_status
}

# Function to verify git repository setup
verify_git_setup() {
    log_message "Verifying git repository setup..."
    
    cd "$GIT_REPO_DIR" || {
        log_message "ERROR: Cannot change to repo directory $GIT_REPO_DIR"
        return 1
    }
    
    # Check if this is a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_message "ERROR: Not a git repository"
        return 1
    fi
    
    # Check if win-version branch exists
    if ! git show-ref --verify --quiet "refs/heads/$GIT_BRANCH"; then
        log_message "WARNING: $GIT_BRANCH branch does not exist locally"
        
        # Check if it exists remotely
        if git ls-remote --heads origin "$GIT_BRANCH" | grep -q "$GIT_BRANCH"; then
            log_message "Found $GIT_BRANCH branch remotely, creating local tracking branch..."
            git fetch origin "$GIT_BRANCH":"$GIT_BRANCH" >> "$LOG_FILE" 2>&1
            git checkout "$GIT_BRANCH" >> "$LOG_FILE" 2>&1
        else
            log_message "ERROR: $GIT_BRANCH branch not found locally or remotely"
            return 1
        fi
    fi
    
    # Setup git configuration
    setup_git_config
    
    log_message "Git repository setup verified successfully"
    return 0
}

# Main execution function
main() {
    log_message "=== Starting daily nifty execution cycle ==="
    
    # Verify git setup first
    if ! verify_git_setup; then
        log_message "ERROR: Git setup verification failed, aborting execution"
        return 1
    fi
    
    # Step 1: Git pull with conflict resolution
    if ! safe_git_pull; then
        log_message "ERROR: Git pull failed, aborting execution"
        return 1
    fi
    
    # Step 2: Run the main script
    if ! run_nifty_script; then
        log_message "WARNING: nifty_main.py execution had issues"
    fi
    
    # Step 3: Git push (skip if authentication isn't setup)
    if ! safe_git_push; then
        log_message "WARNING: Git push failed due to authentication. Please set up SSH keys for automated pushes."
    fi
    
    log_message "=== Daily nifty execution cycle completed ==="
    return 0
}

# Run main function and capture exit status
main "$@"
exit_status=$?

# Log final status
if [ $exit_status -eq 0 ]; then
    log_message "Daily runner completed successfully"
else
    log_message "Daily runner completed with errors (exit code: $exit_status)"
fi

exit $exit_status
