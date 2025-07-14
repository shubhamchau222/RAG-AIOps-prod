# Lock dependencies
if ! uv lock; then
    echo "dependencies are an issue (uv lock failed)"
    exit 1
fi

# Sync dependencies
if ! uv sync; then
    echo "dependencies are an issue (uv sync failed)"
    exit 1
fi

# Success
echo "dependencies are installed"
