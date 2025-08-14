# Vercel Python detection helper
from social_media_manager.wsgi import application

# This helps Vercel detect that this is a Python project
if __name__ == "__main__":
    print("Django WSGI application ready")
