from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import os

@csrf_exempt
def facebook_test_page(request):
    """Serve the Facebook test HTML page"""
    
    # Read the HTML file
    html_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'facebook_test.html')
    
    try:
        with open(html_file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()
        
        return HttpResponse(html_content, content_type='text/html')
    except FileNotFoundError:
        return HttpResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Page Not Found</title>
        </head>
        <body>
            <h1>Facebook Test Page Not Found</h1>
            <p>The facebook_test.html file could not be found.</p>
            <p>Please ensure the file exists in the backend directory.</p>
        </body>
        </html>
        """, content_type='text/html')
