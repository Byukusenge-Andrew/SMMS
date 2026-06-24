import os
import mimetypes
from django.conf import settings
from django.http import JsonResponse, HttpResponse, Http404, FileResponse
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone

ALLOWED_LOG_FILES = ['django.log', 'security.log', 'data_isolation.log']
LOGS_DIR = os.path.join(settings.BASE_DIR, 'logs')

def get_log_filepath(filename):
    """Safely get the path of an allowed log file and prevent path traversal."""
    if filename not in ALLOWED_LOG_FILES:
        return None
    
    # Ensure logs directory exists
    if not os.path.exists(LOGS_DIR):
        try:
            os.makedirs(LOGS_DIR, exist_ok=True)
        except Exception:
            return None

    filepath = os.path.join(LOGS_DIR, filename)
    # Canonicalize paths
    real_logs_dir = os.path.realpath(LOGS_DIR)
    real_filepath = os.path.realpath(filepath)
    if not real_filepath.startswith(real_logs_dir):
        return None
    return real_filepath

def tail_file(filepath, max_lines=1000):
    """Read the last N lines of a file efficiently backwards."""
    if not filepath or not os.path.exists(filepath):
        return []
        
    lines = []
    buffer_size = 8192
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            f.seek(0, os.SEEK_END)
            file_size = f.tell()
            pos = file_size
            remainder = ""
            
            while pos > 0 and len(lines) < max_lines:
                read_size = min(buffer_size, pos)
                pos -= read_size
                f.seek(pos)
                chunk = f.read(read_size)
                
                chunk = chunk + remainder
                chunk_lines = chunk.split('\n')
                
                if pos > 0:
                    remainder = chunk_lines[0]
                    chunk_lines = chunk_lines[1:]
                else:
                    remainder = ""
                
                lines = chunk_lines + lines
    except Exception:
        # Fallback to simple read if seek fails
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
        except Exception:
            return []
            
    # Clean up line endings and filter empty lines at the very end
    lines = [line.rstrip('\r\n') for line in lines if line.strip()]
    return lines[-max_lines:]

@staff_member_required
def log_viewer_html(request):
    """Renders the HTML log visualizer dashboard."""
    return render(request, "core/logs_visualizer.html", {
        "allowed_files": ALLOWED_LOG_FILES
    })

@staff_member_required
def log_list_api(request):
    """JSON API to list allowed log files and their metadata."""
    log_list = []
    
    for filename in ALLOWED_LOG_FILES:
        filepath = get_log_filepath(filename)
        if filepath and os.path.exists(filepath):
            stat = os.stat(filepath)
            size = stat.st_size
            modified = timezone.make_aware(timezone.datetime.fromtimestamp(stat.st_mtime))
            
            # Format size
            if size < 1024:
                size_formatted = f"{size} B"
            elif size < 1024 * 1024:
                size_formatted = f"{size / 1024:.2f} KB"
            else:
                size_formatted = f"{size / (1024 * 1024):.2f} MB"
                
            log_list.append({
                "name": filename,
                "size_bytes": size,
                "size_formatted": size_formatted,
                "modified_at": modified.isoformat(),
                "exists": True
            })
        else:
            log_list.append({
                "name": filename,
                "size_bytes": 0,
                "size_formatted": "0 B",
                "modified_at": None,
                "exists": False
            })
            
    return JsonResponse({"success": True, "logs": log_list})

@staff_member_required
def log_content_api(request, filename):
    """JSON API to fetch lines of a log file, with filters and limits."""
    filepath = get_log_filepath(filename)
    if not filepath:
        return JsonResponse({"success": False, "error": "Invalid log filename"}, status=400)
        
    if not os.path.exists(filepath):
        return JsonResponse({"success": True, "lines": [], "info": "File is empty or does not exist yet"})
        
    # Get parameters
    try:
        limit = int(request.GET.get("limit", 1000))
        limit = min(max(limit, 1), 5000)  # Safe range [1, 5000]
    except ValueError:
        limit = 1000
        
    level_filter = request.GET.get("level", "").strip().lower()
    search_query = request.GET.get("search", "").strip().lower()
    reverse = request.GET.get("reverse", "false").lower() == "true"
    
    # Read the tail lines
    # To account for filtered out lines, we read a bit more than the limit
    raw_lines = tail_file(filepath, max_lines=limit * 5 if (level_filter or search_query) else limit)
    
    filtered_lines = []
    for line in raw_lines:
        line_lower = line.lower()
        
        # Apply level filter
        if level_filter:
            # Map level filter to common log formats
            # standard level terms: info, warning, error, critical, debug, exception
            if level_filter == "warning" and "warn" in line_lower:
                pass
            elif level_filter not in line_lower:
                continue
                
        # Apply search query
        if search_query and search_query not in line_lower:
            continue
            
        filtered_lines.append(line)
        
    # Slice to final limit
    if reverse:
        filtered_lines = filtered_lines[::-1]
    
    result_lines = filtered_lines[-limit:] if not reverse else filtered_lines[:limit]
    
    # Return response
    return JsonResponse({
        "success": True,
        "filename": filename,
        "total_lines_read": len(raw_lines),
        "lines": result_lines
    })

@staff_member_required
def log_clear_api(request, filename):
    """API to clear the content of a log file."""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST method required"}, status=405)
        
    filepath = get_log_filepath(filename)
    if not filepath:
        return JsonResponse({"success": False, "error": "Invalid log filename"}, status=400)
        
    if not os.path.exists(filepath):
        return JsonResponse({"success": False, "error": "Log file does not exist"}, status=404)
        
    try:
        with open(filepath, 'w'):
            pass  # Truncates file to 0 size
        return JsonResponse({"success": True, "message": f"Log file '{filename}' cleared successfully"})
    except Exception as e:
        return JsonResponse({"success": False, "error": f"Failed to clear log file: {str(e)}"}, status=500)

@staff_member_required
def log_download_api(request, filename):
    """API view to download the log file directly."""
    filepath = get_log_filepath(filename)
    if not filepath or not os.path.exists(filepath):
        raise Http404("Log file not found")
        
    try:
        response = FileResponse(open(filepath, 'rb'), content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        return HttpResponse(f"Error downloading log file: {str(e)}", status=500)
