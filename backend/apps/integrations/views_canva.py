"""Canva OAuth Integration Views

Implements Authorization Code flow for Canva using configurable endpoints.
Environment variables expected (configure in settings or .env):
  CANVA_CLIENT_ID
  CANVA_CLIENT_SECRET
  CANVA_REDIRECT_URI  (must match app registration)
  CANVA_SCOPES        (space separated; optional)
  CANVA_AUTHORIZE_URL (default placeholder)
  CANVA_TOKEN_URL     (default placeholder)
  CANVA_USERINFO_URL  (optional; if provided will fetch profile)

All external endpoint URLs are intentionally configurable to avoid hard-coding
in case Canva updates paths. Populate them with the correct production values
before use.
"""
from __future__ import annotations

import logging
from typing import Any, Dict
from urllib.parse import urlencode, quote

from django.conf import settings
from django.shortcuts import redirect
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from .models import IntegrationConnection, IntegrationProvider

logger = logging.getLogger(__name__)


def _setting(name: str, default: str | None = None) -> str | None:
    return getattr(settings, name, None) or default


def _canva_config() -> Dict[str, str | None]:
    return {
        'client_id': _setting('CANVA_CLIENT_ID'),
        'client_secret': _setting('CANVA_CLIENT_SECRET'),
        'redirect_uri': _setting('CANVA_REDIRECT_URI'),
        'scopes': _setting('CANVA_SCOPES', 'openid profile email'),
        # Placeholders – MUST be set to real production endpoints
        'authorize_url': _setting('CANVA_AUTHORIZE_URL', 'https://api.canva.com/oauth/authorize'),
        'token_url': _setting('CANVA_TOKEN_URL', 'https://api.canva.com/oauth/token'),
        'userinfo_url': _setting('CANVA_USERINFO_URL'),
    }


@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([permissions.IsAuthenticated])
def canva_authorize(request):
    """Return Canva OAuth authorize URL with CSRF state saved in session.

    Frontend should open this URL in a popup. Upon redirect back to callback,
    the SPA route /dashboard/integrations/canva/callback will finalize binding
    by calling canva_callback (JSON) + canva_bind_tokens.
    """
    cfg = _canva_config()
    missing = [k for k in ('client_id', 'redirect_uri') if not cfg.get(k)]
    if missing:
        return Response({'success': False, 'error': f"Missing Canva config: {', '.join(missing)}"}, status=500)

    import secrets
    state_val = secrets.token_urlsafe(16)
    request.session['canva_oauth'] = {
        'state': state_val,
        'redirect_uri': cfg['redirect_uri'],
    }
    request.session.modified = True

    params = {
        'response_type': 'code',
        'client_id': cfg['client_id'],
        'redirect_uri': cfg['redirect_uri'],
        'scope': cfg['scopes'],
        'state': state_val,
    }
    authorize_url = f"{cfg['authorize_url']}?{urlencode(params)}"
    return Response({'success': True, 'authorize_url': authorize_url})


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def canva_callback(request):
    """Handle Canva OAuth callback.

    If browser navigation (no JSON Accept), redirect to SPA route preserving code & state.
    If JSON (frontend XHR), exchange code for tokens and return payload.
    """
    code = request.GET.get('code')
    state = request.GET.get('state')
    error = request.GET.get('error')
    accept = request.META.get('HTTP_ACCEPT', '') or ''
    cfg = _canva_config()

    # Redirect to SPA if this is a plain browser navigation
    if 'application/json' not in accept:
        frontend_base = getattr(settings, 'FRONTEND_URL', '').rstrip('/')
        if frontend_base:
            target = f"{frontend_base}/dashboard/integrations/canva/callback"
            sep = '?' if ('?' not in target) else '&'
            pieces = []
            if error:
                pieces.append(f"error={quote(error)}")
            if code:
                pieces.append(f"code={quote(code)}")
            if state:
                pieces.append(f"state={quote(state)}")
            if pieces:
                target = f"{target}{sep}{'&'.join(pieces)}"
            return redirect(target)
        # If no frontend URL configured, fall through to JSON mode

    if error:
        return Response({'success': False, 'error': error}, status=400)
    if not code:
        return Response({'success': False, 'error': 'Missing authorization code'}, status=400)

    sess = request.session.get('canva_oauth') or {}
    expected_state = sess.get('state')
    if expected_state and state and expected_state != state:
        try:
            del request.session['canva_oauth']
        except Exception:
            pass
        return Response({'success': False, 'error': 'Invalid OAuth state'}, status=400)

    # Exchange code for tokens
    token_payload = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': cfg.get('redirect_uri'),
        'client_id': cfg.get('client_id'),
        'client_secret': cfg.get('client_secret'),
    }
    if not cfg.get('client_id') or not cfg.get('client_secret'):
        return Response({'success': False, 'error': 'Server missing Canva client credentials'}, status=500)

    try:
        import requests
        token_resp = requests.post(cfg['token_url'], data=token_payload, timeout=20)
    except Exception as e:
        logger.error(f"Canva token request failed: {e}")
        return Response({'success': False, 'error': 'Token request failed'}, status=502)

    if token_resp.status_code >= 400:
        err_body: Any
        try:
            err_body = token_resp.json()
        except Exception:
            err_body = token_resp.text
        return Response({'success': False, 'error': err_body}, status=token_resp.status_code)

    token_json = {}
    try:
        token_json = token_resp.json()
    except Exception:
        return Response({'success': False, 'error': 'Invalid token JSON'}, status=502)

    access_token = token_json.get('access_token')
    refresh_token = token_json.get('refresh_token')
    expires_in = token_json.get('expires_in')
    scope_str = token_json.get('scope') or cfg.get('scopes') or ''
    scopes = scope_str.split() if isinstance(scope_str, str) else []

    profile: Dict[str, Any] = {}
    if access_token and cfg.get('userinfo_url'):
        try:
            import requests
            prof_resp = requests.get(cfg['userinfo_url'], headers={'Authorization': f'Bearer {access_token}'}, timeout=15)
            if prof_resp.status_code < 400:
                profile = prof_resp.json() if prof_resp.headers.get('Content-Type', '').startswith('application/json') else {}
        except Exception as e:
            logger.warning(f"Canva userinfo fetch failed: {e}")

    # Clear state
    try:
        del request.session['canva_oauth']
    except Exception:
        pass

    return Response({
        'success': True,
        'provider': 'canva',
        'profile': profile,
        'tokens': {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_in': expires_in,
            'scopes': scopes,
        }
    })


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([permissions.IsAuthenticated])
def canva_bind_tokens(request):
    """Bind Canva tokens to IntegrationConnection for authenticated user.

    Expected JSON: { tokens: { access_token, refresh_token?, expires_in?, scopes?[] }, profile: {...} }
    """
    data = request.data or {}
    tokens = data.get('tokens') or {}
    profile = data.get('profile') or {}
    access_token = tokens.get('access_token')
    if not access_token:
        return Response({'success': False, 'error': 'Missing access_token'}, status=400)

    refresh_token = tokens.get('refresh_token') or ''
    expires_in = tokens.get('expires_in')
    scopes = tokens.get('scopes') or []
    if isinstance(scopes, str):  # allow space separated string
        scopes = scopes.split()

    conn, _ = IntegrationConnection.objects.update_or_create(
        user=request.user,
        provider=IntegrationProvider.CANVA,
        defaults={
            'access_token': access_token,
            'refresh_token': refresh_token,
            'scopes': scopes,
            'metadata': {'profile': profile},
            'active': True,
        }
    )
    if expires_in:
        try:
            conn.token_expires_at = timezone.now() + timezone.timedelta(seconds=int(expires_in))
            conn.save(update_fields=['token_expires_at'])
        except Exception:
            pass

    return Response({'success': True, 'connection_id': str(conn.id)})


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([permissions.IsAuthenticated])
def canva_disconnect(request):
    """Disconnect Canva integration (remove IntegrationConnection)."""
    IntegrationConnection.objects.filter(user=request.user, provider=IntegrationProvider.CANVA).delete()
    return Response({'success': True, 'message': 'Canva disconnected'})
