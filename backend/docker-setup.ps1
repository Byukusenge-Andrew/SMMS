# Quick Docker Setup
# Run this script to get started with Docker development environment

Write-Host "🐳 SMMS Backend Docker Setup" -ForegroundColor Cyan
Write-Host "=============================" -ForegroundColor Cyan

# Check if Docker is running
$dockerRunning = docker ps 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✅ Docker is running" -ForegroundColor Green

# Check if .env file exists
if (!(Test-Path ".env")) {
    Write-Host "📝 Creating .env file from template..." -ForegroundColor Yellow
    Copy-Item ".env.docker" ".env"
    Write-Host "✅ .env file created" -ForegroundColor Green
    Write-Host "⚠️  Please edit .env file with your actual API keys and credentials" -ForegroundColor Yellow
} else {
    Write-Host "✅ .env file already exists" -ForegroundColor Green
}

# Build and start services
Write-Host "🏗️  Building Docker images..." -ForegroundColor Blue
& .\docker-manager.bat build

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Docker images built successfully" -ForegroundColor Green
    
    Write-Host "🚀 Starting development environment..." -ForegroundColor Blue
    & .\docker-manager.bat start
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Development environment started!" -ForegroundColor Green
        
        # Wait for services to be ready
        Write-Host "⏳ Waiting for services to be ready..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
        
        Write-Host "🔧 Running database migrations..." -ForegroundColor Blue
        & .\docker-manager.bat migrate
        
        Write-Host "" 
        Write-Host "🎉 Setup completed successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "📍 Your services are now running:" -ForegroundColor Cyan
        Write-Host "   • Backend API: http://localhost:8000" -ForegroundColor White
        Write-Host "   • Admin Panel: http://localhost:8000/admin" -ForegroundColor White
        Write-Host "   • API Docs: http://localhost:8000/api/docs/" -ForegroundColor White
        Write-Host "   • Database: localhost:5432" -ForegroundColor White
        Write-Host "   • Redis: localhost:6379" -ForegroundColor White
        Write-Host ""
        Write-Host "🛠️  Useful commands:" -ForegroundColor Cyan
        Write-Host "   • View logs: .\docker-manager.bat logs" -ForegroundColor White
        Write-Host "   • Create superuser: .\docker-manager.bat createsuperuser" -ForegroundColor White
        Write-Host "   • Stop services: .\docker-manager.bat stop" -ForegroundColor White
        Write-Host "   • Django shell: .\docker-manager.bat shell" -ForegroundColor White
        Write-Host ""
        Write-Host "📖 For more information, see DOCKER_README.md" -ForegroundColor Cyan
        
    } else {
        Write-Host "❌ Failed to start development environment" -ForegroundColor Red
    }
} else {
    Write-Host "❌ Failed to build Docker images" -ForegroundColor Red
}

Write-Host ""
Read-Host "Press Enter to continue"
