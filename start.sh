#!/bin/bash

# arXiv Paper Fetcher - Start Script

# Function to calculate date range (10 days ago to 4 days ago, i.e., 7 days)
calculate_date_range() {
    # Get current date
    local today=$(date +%Y-%m-%d)
    
    # Calculate start_date (10 days ago) and end_date (4 days ago)
    # This gives us a 7-day range
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS date command
        local start_date=$(date -v-10d -j -f "%Y-%m-%d" "$today" +%Y-%m-%d 2>/dev/null || date -j -v-10d +%Y-%m-%d)
        local end_date=$(date -v-4d -j -f "%Y-%m-%d" "$today" +%Y-%m-%d 2>/dev/null || date -j -v-4d +%Y-%m-%d)
    else
        # Linux date command
        local start_date=$(date -d "10 days ago" +%Y-%m-%d)
        local end_date=$(date -d "4 days ago" +%Y-%m-%d)
    fi
    
    echo "$start_date $end_date"
}

# Function to regenerate config.json from default_config.py
regenerate_config() {
    local start_date=${1:-""}
    local end_date=${2:-""}
    
    echo "🔄 Regenerating config.json from default_config.py..."
    
    config_path="backend/data/config.json"
    
    # Remove existing config.json if it exists
    if [ -f "$config_path" ]; then
        rm "$config_path"
        echo "   ✓ Removed existing config.json"
    fi
    
    # Create data directory if it doesn't exist
    mkdir -p backend/data
    
    # Generate new config.json using Python
    cd backend
    if [ -n "$start_date" ] && [ -n "$end_date" ]; then
        echo "   📅 Using custom date range: $start_date to $end_date"
        python3 << EOF
from pathlib import Path
from models import Config
from default_config import DEFAULT_CONFIG

config_path = Path("data/config.json")
config_path.parent.mkdir(parents=True, exist_ok=True)

# Create config with custom dates
config_dict = DEFAULT_CONFIG.copy()
config_dict["start_date"] = "$start_date"
config_dict["end_date"] = "$end_date"

config = Config(**config_dict)
config.save(str(config_path))
print(f"   ✓ Created new config.json at {config_path}")
print(f"   ✓ Start date: {config.start_date}")
print(f"   ✓ End date: {config.end_date}")
EOF
    else
        python3 << 'EOF'
from pathlib import Path
from models import Config
from default_config import DEFAULT_CONFIG

config_path = Path("data/config.json")
config_path.parent.mkdir(parents=True, exist_ok=True)

config = Config(**DEFAULT_CONFIG)
config.save(str(config_path))
print(f"   ✓ Created new config.json at {config_path}")
print(f"   ✓ Start date: {config.start_date} (default)")
print(f"   ✓ End date: {config.end_date} (default)")
EOF
    fi
    
    config_result=$?
    cd ..
    
    if [ $config_result -eq 0 ]; then
        echo "✅ Config regeneration completed!"
    else
        echo "⚠️  Config regeneration failed"
    fi
    
    return $config_result
}

# Function to upload markdown files to GitHub
upload_to_github() {
    local markdown_dir="backend/data/markdown_export"
    local github_repo="https://github.com/insight-rain/insight-rain.github.io.git"
    local github_dir="github_pages"
    
    echo "📤 Uploading markdown files to GitHub..."
    
    # Check if git is available
    if ! command -v git &> /dev/null; then
        echo "⚠️  Git is not installed, skipping GitHub upload"
        return 1
    fi
    
    # Check if markdown directory exists and has folders
    if [ ! -d "$markdown_dir" ]; then
        echo "⚠️  Markdown directory not found: $markdown_dir, skipping upload"
        return 1
    fi
    
    # Get the latest folder (by modification time)
    local latest_folder=$(find "$markdown_dir" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
    # If find doesn't support -printf, use alternative method
    if [ -z "$latest_folder" ]; then
        latest_folder=$(ls -td "$markdown_dir"/*/ 2>/dev/null | head -1)
        latest_folder="${latest_folder%/}"  # Remove trailing slash
    fi
    
    if [ -z "$latest_folder" ] || [ ! -d "$latest_folder" ]; then
        echo "⚠️  No markdown folders found in $markdown_dir, skipping upload"
        return 1
    fi
    
    local foldername=$(basename "$latest_folder")
    echo "   Latest folder: $foldername"
    
    # Clone or update GitHub repository
    if [ ! -d "$github_dir" ]; then
        echo "   📥 Cloning GitHub repository..."
        git clone "$github_repo" "$github_dir" 2>&1 | grep -v "Cloning into" || {
            echo "⚠️  Failed to clone repository. Make sure you have access."
            return 1
        }
    else
        echo "   🔄 Updating GitHub repository..."
        cd "$github_dir"
        git pull origin main 2>&1 | grep -v "Already up to date" || git pull origin master 2>&1 | grep -v "Already up to date" || true
        cd ..
    fi
    
    # Copy latest folder to GitHub directory
    if [ -d "$github_dir" ]; then
        echo "   📋 Copying folder $foldername to GitHub repository..."
        cp -r "$latest_folder" "$github_dir/"
        
        cd "$github_dir"
        
        # Configure git if needed
        git config user.name "arXiv AI Reader" > /dev/null 2>&1 || true
        git config user.email "arxiv-reader@localhost" > /dev/null 2>&1 || true
        
        # Add folder and all its contents
        git add "$foldername" 2>&1 | grep -v "warning:" || true
        
        # Check if there are changes to commit
        if git diff --staged --quiet; then
            echo "   ℹ️  No changes to commit (file already exists and is identical)"
        else
            local commit_msg="Auto-update: Add paper export $(date '+%Y-%m-%d %H:%M:%S')"
            git commit -m "$commit_msg" 2>&1 | grep -v "nothing to commit" || {
                echo "   ℹ️  Nothing to commit"
            }
            
            # Push to GitHub
            echo "   🚀 Pushing to GitHub..."
            git push origin main 2>&1 | grep -v "Everything up-to-date" || \
            git push origin master 2>&1 | grep -v "Everything up-to-date" || {
                echo "⚠️  Failed to push to GitHub. Check your credentials."
                cd ..
                return 1
            }
            
            echo "   ✅ Successfully pushed to GitHub!"
        fi
        
        cd ..
    else
        echo "⚠️  GitHub directory not found"
        return 1
    fi
    
    return 0
}

# Function to clean up paper JSON files
cleanup_papers() {
    local papers_dir="backend/data/papers"
    
    if [ ! -d "$papers_dir" ]; then
        return 0
    fi
    
    # Count JSON files
    local count=$(find "$papers_dir" -name "*.json" -type f | wc -l)
    
    if [ "$count" -eq 0 ]; then
        return 0
    fi
    
    echo "🧹 Cleaning up $count paper files from $papers_dir..."
    find "$papers_dir" -name "*.json" -type f -delete
    
    if [ $? -eq 0 ]; then
        echo "   ✓ Cleaned up $count paper files"
        return 0
    else
        echo "   ⚠️  Failed to clean up paper files"
        return 1
    fi
}

# Function to export papers to markdown
export_to_markdown() {
    local min_score=${1:-6.0}
    local output_file=${2:-""}
    local auto_upload=${3:-true}
    
    echo "📝 Exporting papers to markdown..."
    echo "   Minimum score: $min_score"
    echo "   Output: folder named after date range (one file per paper)"
    
    cd backend
    if [ -n "$output_file" ]; then
        python3 exporter.py --min-score "$min_score" --output-file "$output_file"
    else
        python3 exporter.py --min-score "$min_score"
    fi
    export_result=$?
    cd ..
    
    if [ $export_result -eq 0 ]; then
        echo "✅ Markdown export completed!"
        
        # Auto-upload to GitHub if enabled
        if [ "$auto_upload" = "true" ]; then
            upload_to_github
            upload_result=$?
            
            # Clean up paper files after successful export and upload
            if [ $upload_result -eq 0 ]; then
                cleanup_papers
            fi
        else
            # Clean up paper files even if upload is disabled
            cleanup_papers
        fi
    else
        echo "⚠️  Markdown export failed"
    fi
    
    return $export_result
}

# Parse command line arguments for date range
START_DATE=""
END_DATE=""
REMAINING_ARGS=()
EXPORT_MODE=false
SINGLE_RUN=false
AUTO_DATE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --start-date)
            START_DATE="$2"
            shift 2
            ;;
        --end-date)
            END_DATE="$2"
            shift 2
            ;;
        --auto-date|--auto)
            # Auto-calculate date range (10 days ago to 4 days ago)
            AUTO_DATE=true
            shift
            ;;
        --once|--single-run)
            # Single run mode: run once and exit
            SINGLE_RUN=true
            shift
            ;;
        --export|-e)
            # Handle export flag separately
            EXPORT_MODE=true
            REMAINING_ARGS+=("$1")
            shift
            ;;
        export)
            # Export only mode
            EXPORT_MODE=true
            REMAINING_ARGS+=("$1")
            shift
            ;;
        docker)
            # Docker mode - pass through
            REMAINING_ARGS+=("$1")
            shift
            ;;
        *)
            # Check if it looks like a date (YYYY-MM-DD format)
            if [[ "$1" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
                if [ -z "$START_DATE" ]; then
                    START_DATE="$1"
                elif [ -z "$END_DATE" ]; then
                    END_DATE="$1"
                else
                    REMAINING_ARGS+=("$1")
                fi
            else
                REMAINING_ARGS+=("$1")
            fi
            shift
            ;;
    esac
done

# Auto-calculate date range if requested
if [ "$AUTO_DATE" = true ]; then
    echo "📅 Auto-calculating date range (10 days ago to 4 days ago)..."
    date_range=($(calculate_date_range))
    START_DATE="${date_range[0]}"
    END_DATE="${date_range[1]}"
    echo "   Calculated range: $START_DATE to $END_DATE"
fi

# Restore remaining arguments for further processing
set -- "${REMAINING_ARGS[@]}"

# Handle export-only mode (before other checks)
if [ "$1" == "export" ]; then
    # Regenerate config with date range if provided
    if [ -n "$START_DATE" ] || [ -n "$END_DATE" ]; then
        regenerate_config "$START_DATE" "$END_DATE"
        echo ""
    fi
    # Check if --no-upload flag is set (check remaining args)
    local no_upload=false
    for arg in "${REMAINING_ARGS[@]}"; do
        if [ "$arg" == "--no-upload" ]; then
            no_upload=true
            break
        fi
    done
    if [ "$no_upload" = true ]; then
        export_to_markdown "${2:-6.0}" "${3:-}" "false"
    else
        export_to_markdown "${2:-6.0}" "${3:-}" "true"
    fi
    exit $?
fi

echo "🚀 Starting arXiv Paper Fetcher..."

# Check if DEEPSEEK_API_KEY is set
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "⚠️  DEEPSEEK_API_KEY not set"
    echo "Please run: export DEEPSEEK_API_KEY='your-api-key'"
    exit 1
fi

# Create data directory
mkdir -p data/papers

# Regenerate config.json from default_config.py with date range
regenerate_config "$START_DATE" "$END_DATE"
echo ""

# Build static assets with cache busting
echo "🔨 Building static assets..."
python3 build_static.py
if [ $? -ne 0 ]; then
    echo "⚠️  Static assets build failed, continuing with source files..."
fi

# Export papers to markdown before starting server (if --export flag is set)
if [ "$1" == "--export" ] || [ "$1" == "-e" ]; then
    # Check if --no-upload flag is set (check remaining args)
    local no_upload=false
    for arg in "${REMAINING_ARGS[@]}"; do
        if [ "$arg" == "--no-upload" ]; then
            no_upload=true
            break
        fi
    done
    if [ "$no_upload" = true ]; then
        export_to_markdown "${2:-6.0}" "${3:-}" "false"
    else
        export_to_markdown "${2:-6.0}" "${3:-}" "true"
    fi
    echo ""
fi

# Function to check and handle port conflicts
check_port() {
    local port=${1:-5000}
    
    # Check if port is in use
    if lsof -i :$port >/dev/null 2>&1 || netstat -tuln 2>/dev/null | grep -q ":$port " || ss -tuln 2>/dev/null | grep -q ":$port "; then
        echo "⚠️  Port $port is already in use"
        echo "   Trying to find the process..."
        
        # Try to find the process
        local pid=$(lsof -ti :$port 2>/dev/null || netstat -tuln 2>/dev/null | grep ":$port " | awk '{print $NF}' | cut -d'/' -f1 | head -1)
        
        if [ -n "$pid" ]; then
            echo "   Found process PID: $pid"
            echo "   You can kill it with: kill $pid"
            echo "   Or use a different port with: PORT=8000 ./start.sh"
            return 1
        else
            echo "   Could not identify the process, but port is in use"
            return 1
        fi
    fi
    
    return 0
}

# Check if running with Docker
if [ "$1" == "docker" ]; then
    echo "🐳 Starting with Docker..."
    docker-compose up --build
else
    # Check for custom port from environment variable
    PORT=${PORT:-5000}
    
    # Check port availability
    if ! check_port $PORT; then
        echo ""
        echo "💡 Solutions:"
        echo "   1. Kill the existing process: kill $(lsof -ti :$PORT 2>/dev/null | head -1)"
        echo "   2. Use a different port: PORT=8000 ./start.sh"
        echo "   3. Wait for the existing process to finish"
        exit 1
    fi
    
    echo "✅ Starting backend server..."
    echo "📍 URL: http://localhost:$PORT"
    echo "📖 Features:"
    echo "   - Markdown 渲染 Q&A"
    echo "   - 中文回答"
    echo "   - 相关性打分 (0-10)"
    echo "   - 按相关性/最新/收藏排序"
    echo "   - Hide/Star 功能"
    echo "   - Keyword 筛选"
    echo "   - Markdown 导出功能"
    echo ""
    echo "💡 Tips:"
    echo "   - Run './start.sh --auto-date --once' for weekly automated runs"
    echo "   - Run './start.sh export' to export papers only (auto-uploads to GitHub)"
    echo "   - Run './start.sh --export' to export before starting server (auto-uploads to GitHub)"
    echo "   - Run './start.sh --export 6.0' to customize export (default: 6.0)"
    echo "   - Run './start.sh export 6.0 --no-upload' to skip GitHub upload"
    echo "   - Run './start.sh 2025-12-28 2025-12-29' to set date range"
    echo "   - Run './start.sh --start-date 2025-12-28 --end-date 2025-12-29' to set date range"
    echo "   - Run './start.sh --auto-date' to auto-calculate date range (10 days ago to 4 days ago)"
    echo "   - Run './start.sh --once' or './start.sh --single-run' to run once and exit"
    echo "   - Run './start.sh --auto-date --once' for weekly automated runs"
    echo "   - Run 'PORT=8000 ./start.sh' to use a different port"
    echo "   - Config.json is automatically regenerated from default_config.py on startup"
    echo "   - Markdown files are automatically uploaded to GitHub after export"
    echo ""
    
    # Set single run mode if requested
    if [ "$SINGLE_RUN" = true ]; then
        export SINGLE_RUN="1"
        echo "🔄 Running in single-run mode (will exit after completion)"
        echo ""
    fi
    
    cd backend && PORT=$PORT python api.py
fi

