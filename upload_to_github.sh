#!/bin/bash

# Upload markdown files/folders to GitHub
# Usage: ./upload_to_github.sh [folder_path]

MARKDOWN_DIR="backend/data/markdown_export"
GITHUB_REPO="https://github.com/insight-rain/insight-rain.github.io.git"
GITHUB_DIR="github_pages"

# If a specific folder is provided, use it; otherwise use the latest folder
if [ -n "$1" ]; then
    LATEST_FOLDER="$1"
else
    # Find the latest folder (by modification time)
    LATEST_FOLDER=$(find "$MARKDOWN_DIR" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
    # If find doesn't support -printf, use alternative method
    if [ -z "$LATEST_FOLDER" ]; then
        LATEST_FOLDER=$(ls -td "$MARKDOWN_DIR"/*/ 2>/dev/null | head -1)
        LATEST_FOLDER="${LATEST_FOLDER%/}"  # Remove trailing slash
    fi
fi

if [ -z "$LATEST_FOLDER" ] || [ ! -d "$LATEST_FOLDER" ]; then
    echo "⚠️  No markdown folder found in $MARKDOWN_DIR"
    exit 1
fi

FOLDERNAME=$(basename "$LATEST_FOLDER")
echo "📤 Uploading folder $FOLDERNAME to GitHub..."

# Check if git is available
if ! command -v git &> /dev/null; then
    echo "⚠️  Git is not installed"
    exit 1
fi

# Clone or update GitHub repository
if [ ! -d "$GITHUB_DIR" ]; then
    echo "   📥 Cloning GitHub repository..."
    git clone "$GITHUB_REPO" "$GITHUB_DIR" 2>&1 | grep -v "Cloning into" || {
        echo "⚠️  Failed to clone repository"
        exit 1
    }
else
    echo "   🔄 Updating GitHub repository..."
    cd "$GITHUB_DIR"
    git pull origin main 2>&1 | grep -v "Already up to date" || \
    git pull origin master 2>&1 | grep -v "Already up to date" || true
    cd ..
fi

# Copy folder to GitHub directory
if [ -d "$GITHUB_DIR" ]; then
    echo "   📋 Copying folder $FOLDERNAME to GitHub repository..."
    # Copy the entire folder
    cp -r "$LATEST_FOLDER" "$GITHUB_DIR/"
    
    cd "$GITHUB_DIR"
    
    # Configure git if needed
    git config user.name "arXiv AI Reader" > /dev/null 2>&1 || true
    git config user.email "arxiv-reader@localhost" > /dev/null 2>&1 || true
    
    # Add folder and all its contents
    git add "$FOLDERNAME" 2>&1 | grep -v "warning:" || true
    
    # Check if there are changes to commit
    if git diff --staged --quiet; then
        echo "   ℹ️  No changes to commit"
    else
        COMMIT_MSG="Auto-update: Add paper export $(date '+%Y-%m-%d %H:%M:%S')"
        git commit -m "$COMMIT_MSG" 2>&1 | grep -v "nothing to commit" || {
            echo "   ℹ️  Nothing to commit"
            cd ..
            exit 0
        }
        
        # Push to GitHub
        echo "   🚀 Pushing to GitHub..."
        git push origin main 2>&1 | grep -v "Everything up-to-date" || \
        git push origin master 2>&1 | grep -v "Everything up-to-date" || {
            echo "⚠️  Failed to push to GitHub"
            cd ..
            exit 1
        }
        
        echo "   ✅ Successfully pushed to GitHub!"
    fi
    
    cd ..
else
    echo "⚠️  GitHub directory not found"
    exit 1
fi

exit 0

