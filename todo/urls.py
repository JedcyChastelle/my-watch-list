from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('mcp_server.urls')),  # publie le serveur MCP sur /mcp
    path('', include('tasks.urls')),
]