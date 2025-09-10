#!/bin/bash
# TikTok OAuth Setup with ngrok

echo "🚀 Setting up TikTok OAuth with ngrok..."

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok not found. Please install it first:"
    echo "   1. Download from https://ngrok.com/download"
    echo "   2. Or install via: choco install ngrok"
    exit 1
fi

# Start Django server
echo "📦 Starting Django server..."
cd "$(dirname "$0")"
source venv/Scripts/activate
python manage.py runserver &
DJANGO_PID=$!

# Wait for Django to start
sleep 3

# Start ngrok tunnel
echo "🌐 Starting ngrok tunnel..."
ngrok http 8000 &
NGROK_PID=$!

# Wait for ngrok to start
sleep 5

# Get ngrok URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | python -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for tunnel in data['tunnels']:
        if tunnel['proto'] == 'https':
            print(tunnel['public_url'])
            break
except:
    pass
")

if [ -n "$NGROK_URL" ]; then
    echo "✅ ngrok tunnel created: $NGROK_URL"
    echo ""
    echo "🔧 Next steps:"
    echo "1. Update your .env file:"
    echo "   TIKTOK_REDIRECT_URI=$NGROK_URL/api/integrations/tiktok/callback/"
    echo ""
    echo "2. Update TikTok Developer Console:"
    echo "   Web/Desktop URL: $NGROK_URL"
    echo "   Login Kit Redirect URI: $NGROK_URL/api/integrations/tiktok/callback/"
    echo ""
    echo "3. Test TikTok OAuth at: $NGROK_URL"
    echo ""
    echo "Press Ctrl+C to stop both Django and ngrok"
else
    echo "❌ Could not get ngrok URL"
fi

# Wait for user to stop
wait

# Cleanup
kill $DJANGO_PID $NGROK_PID 2>/dev/null
