@echo off
REM TikTok OAuth Setup with ngrok for Windows

echo 🚀 Setting up TikTok OAuth with ngrok...

REM Check if ngrok is installed
where ngrok >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ ngrok not found. Please install it first:
    echo    1. Download from https://ngrok.com/download
    echo    2. Or install via: choco install ngrok
    pause
    exit /b 1
)

REM Start Django server
echo 📦 Starting Django server...
start "Django Server" cmd /k "venv\Scripts\activate && python manage.py runserver"

REM Wait for Django to start
timeout /t 5 /nobreak

REM Start ngrok tunnel  
echo 🌐 Starting ngrok tunnel...
start "ngrok" cmd /k "ngrok http 8000"

REM Wait for ngrok to start
timeout /t 5 /nobreak

echo ✅ Services started!
echo.
echo 🔧 Next steps:
echo 1. Check the ngrok terminal for your HTTPS URL (something like https://abc123.ngrok.io)
echo 2. Update your .env file:
echo    TIKTOK_REDIRECT_URI=https://your-ngrok-url.ngrok.io/api/integrations/tiktok/callback/
echo.
echo 3. Update TikTok Developer Console:
echo    Web/Desktop URL: https://your-ngrok-url.ngrok.io
echo    Login Kit Redirect URI: https://your-ngrok-url.ngrok.io/api/integrations/tiktok/callback/
echo.
echo 4. Test TikTok OAuth at your ngrok URL
echo.
echo Press any key to continue...
pause
