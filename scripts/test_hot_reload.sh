#!/bin/bash
# Test configuration hot-reload functionality

echo "🧪 Testing Configuration Hot-Reload"
echo "===================================="

# Start config watcher in background
python config_manager.py &
PID=$!

sleep 3

echo ""
echo "Current config values:"
python -c "
from config_manager import get_config
config = get_config()
print(f'  Base delay: {config.scraper.rate_limiting.base_delay}')
print(f'  Max workers: {config.scraper.concurrency.max_workers}')
"

echo ""
echo "Modifying config.yaml..."
# Change base_delay from 2.0 to 5.0
sed -i 's/base_delay: 2.0/base_delay: 5.0/' config.yaml
sed -i 's/max_workers: 8/max_workers: 16/' config.yaml

sleep 3

echo ""
echo "New config values (should reflect changes):"
python -c "
from config_manager import get_config
config = get_config()
print(f'  Base delay: {config.scraper.rate_limiting.base_delay}')
print(f'  Max workers: {config.scraper.concurrency.max_workers}')
"

# Restore original
echo ""
echo "Restoring original config..."
sed -i 's/base_delay: 5.0/base_delay: 2.0/' config.yaml
sed -i 's/max_workers: 16/max_workers: 8/' config.yaml

# Cleanup
kill $PID 2>/dev/null

echo ""
echo "✅ Hot-reload test complete!"
