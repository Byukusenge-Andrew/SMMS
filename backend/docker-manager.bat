@echo off
REM Docker Management Script for SMMS Backend (Windows)

setlocal enabledelayedexpansion

REM Functions
:print_status
echo [INFO] %~1
goto :eof

:print_warning
echo [WARNING] %~1
goto :eof

:print_error
echo [ERROR] %~1
goto :eof

REM Main script logic
if "%1"=="build" goto build_dev
if "%1"=="build-prod" goto build_prod
if "%1"=="start" goto start_dev
if "%1"=="up" goto start_dev
if "%1"=="start-prod" goto start_prod
if "%1"=="up-prod" goto start_prod
if "%1"=="stop" goto stop_dev
if "%1"=="down" goto stop_dev
if "%1"=="stop-prod" goto stop_prod
if "%1"=="down-prod" goto stop_prod
if "%1"=="logs" goto logs_dev
if "%1"=="logs-prod" goto logs_prod
if "%1"=="shell" goto shell
if "%1"=="migrate" goto migrate
if "%1"=="makemigrations" goto makemigrations
if "%1"=="collectstatic" goto collectstatic
if "%1"=="createsuperuser" goto createsuperuser
if "%1"=="test" goto test
if "%1"=="cleanup" goto cleanup
if "%1"=="reset" goto reset
if "%1"=="backup-db" goto backup_db
if "%1"=="restore-db" goto restore_db
if "%1"=="psql" goto psql
goto usage

:build_dev
call :print_status "Building development Docker images..."
docker-compose build
goto :eof

:build_prod
call :print_status "Building production Docker images..."
docker-compose -f docker-compose.prod.yml build
goto :eof

:start_dev
call :print_status "Starting development environment..."
docker-compose up -d
call :print_status "Development environment started!"
call :print_status "Backend: http://localhost:8000"
call :print_status "Database: localhost:5432"
call :print_status "Redis: localhost:6379"
goto :eof

:start_prod
call :print_status "Starting production environment..."
docker-compose -f docker-compose.prod.yml up -d
call :print_status "Production environment started!"
goto :eof

:stop_dev
call :print_status "Stopping development environment..."
docker-compose down
goto :eof

:stop_prod
call :print_status "Stopping production environment..."
docker-compose -f docker-compose.prod.yml down
goto :eof

:logs_dev
docker-compose logs -f
goto :eof

:logs_prod
docker-compose -f docker-compose.prod.yml logs -f
goto :eof

:shell
call :print_status "Opening Django shell in container..."
docker-compose exec backend python manage.py shell
goto :eof

:migrate
call :print_status "Running database migrations..."
docker-compose exec backend python manage.py migrate
goto :eof

:makemigrations
call :print_status "Creating database migrations..."
docker-compose exec backend python manage.py makemigrations
goto :eof

:collectstatic
call :print_status "Collecting static files..."
docker-compose exec backend python manage.py collectstatic --noinput
goto :eof

:createsuperuser
call :print_status "Creating superuser..."
docker-compose exec backend python manage.py createsuperuser
goto :eof

:test
call :print_status "Running tests..."
docker-compose exec backend python manage.py test
goto :eof

:backup_db
call :print_status "Creating database backup..."
docker exec smms_postgres_dev pg_dump -U postgres social-media-db > "docker\postgres\backups\smms-backup-%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%.sql"
call :print_status "Database backup created in docker\postgres\backups\"
goto :eof

:restore_db
if "%2"=="" (
    call :print_error "Usage: %0 restore-db backup_file.sql"
    goto :eof
)
call :print_warning "This will replace all data in the database!"
set /p confirm="Are you sure you want to restore from %2? (y/N): "
if /i "!confirm!"=="y" (
    call :print_status "Restoring database from: %2"
    docker cp "%2" smms_postgres_dev:/tmp/restore.sql
    docker exec smms_postgres_dev psql -U postgres -d social-media-db -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
    docker exec smms_postgres_dev psql -U postgres -d social-media-db -f /tmp/restore.sql
    docker exec smms_postgres_dev rm /tmp/restore.sql
    call :print_status "Database restored successfully!"
) else (
    call :print_status "Restore cancelled."
)
goto :eof

:psql
call :print_status "Connecting to PostgreSQL..."
docker exec -it smms_postgres_dev psql -U postgres -d social-media-db
goto :eof

:cleanup
call :print_status "Cleaning up Docker resources..."
docker-compose down -v
docker system prune -f
call :print_status "Cleanup completed!"
goto :eof

:reset
call :print_warning "This will remove all containers, volumes, and data!"
set /p confirm="Are you sure? (y/N): "
if /i "!confirm!"=="y" (
    call :print_status "Resetting environment..."
    docker-compose down -v
    docker-compose up -d
    timeout /t 10 /nobreak >nul
    docker-compose exec backend python manage.py migrate
    call :print_status "Environment reset completed!"
) else (
    call :print_status "Reset cancelled."
)
goto :eof

:usage
echo Usage: %0 {build^|build-prod^|start^|start-prod^|stop^|stop-prod^|logs^|logs-prod^|shell^|migrate^|makemigrations^|collectstatic^|createsuperuser^|test^|cleanup^|reset}
echo.
echo Development Commands:
echo   build         - Build development images
echo   start/up      - Start development environment
echo   stop/down     - Stop development environment
echo   logs          - View development logs
echo.
echo Production Commands:
echo   build-prod    - Build production images
echo   start-prod    - Start production environment
echo   stop-prod     - Stop production environment
echo   logs-prod     - View production logs
echo.
echo Management Commands:
echo   shell         - Open Django shell
echo   migrate       - Run database migrations
echo   makemigrations- Create new migrations
echo   collectstatic - Collect static files
echo   createsuperuser - Create Django superuser
echo   test          - Run tests
echo   backup-db     - Create database backup
echo   restore-db    - Restore database from backup
echo   psql          - Connect to PostgreSQL shell
echo   cleanup       - Clean up Docker resources
echo   reset         - Reset entire environment (WARNING: deletes data^)
exit /b 1
