import json
import logging
from datetime import datetime
import functools
from odoo import http
from odoo.http import request


_logger = logging.getLogger(__name__)


def token_required(f):
    """Decorator to verify the access token"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.httprequest.headers.get('Authorization')
        
        if not token:
            return request.make_response(
                json.dumps({'success': False, 'error': 'missing token'}),
                status=401,
                headers=[('Content-Type', 'application/json')]
            )
        
        try:
            if token.startswith('Bearer '):
                token = token.split(' ')[1]
            
            user = request.env['res.users'].sudo().search([
                ('access_token', '=', token)
            ], limit=1)
            
            if not user or not user.validate_token(token):
                return request.make_response(
                    json.dumps({'success': False, 'error': 'Invalid token'}),
                    status=401,
                    headers=[('Content-Type', 'application/json')]
                )
            
            request.env.user = user
            
        except Exception as e:
            _logger.error("Error token validation: %s", e)
            return request.make_response(
                json.dumps({'success': False, 'error': 'Authentication error'}),
                status=401,
                headers=[('Content-Type', 'application/json')]
            )
        
        return f(*args, **kwargs)
    
    return decorated_function


class AuthController(http.Controller):
    """Authentication controller"""
    @http.route('/api/login', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def api_login(self, **kwargs):
        """
        User authentication and token generation
        POST /api/login
        Headers: {'db' : db_name}
        Body: { "login": "admin", "password": "admin"}
        """
        try:
            db = request.httprequest.headers.get('db')
            data = json.loads(request.httprequest.data.decode('utf-8'))
            login = data.get('login')
            password = data.get('password')
            credentials = {'login': login, 'password': password, 'type': 'password'}

            if not all([db, login, password]):
                return self._error_response('Credentials required', 400)
            
            try:
                request.session.authenticate(db, credentials)
                uid = request.session.uid
            except Exception as e:
                _logger.error("Authentication error: %s", e)
                return self._error_response('Authentication error', 401)
            
            if not uid:
                return self._error_response('Incorrect credentials', 401)
            
            user = request.env['res.users'].sudo().browse(uid)
            token = user.generate_access_token()
            
            return self._success_response("Login successfully",
                        {
                            'user_id': uid,
                            'email': user.email,
                            'token': token
                        })
            
        except json.JSONDecodeError:
            return self._error_response('Invalid JSON format', 400)
        except Exception as e:
            _logger.error("Authentication error: %s", e)
            return self._error_response('Server error', 500)
    
    @http.route('/api/logout', type='http', auth='public', methods=['POST'],
                     csrf=False, cors='*')
    @token_required
    def api_logout(self, **kwargs):
        """
        Loging out user
        POST /api/logout
        Headers: Authorization: Bearer <token>
        """
        try:
            user = request.env.user
            user.invalidate_token()
            return self._success_response("Log out successfully",{})
        except Exception as e:
            _logger.error("Error while logging out: %s", e)
            return self._error_response('Server error', 500)
    
    @http.route('/api/token/verify', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    @token_required
    def verify_token(self, **kwargs):
        """
        Token validation
        GET /api/token/verify
        Headers: Authorization: Bearer <token>
        """
        try:
            user = request.env.user
            return self._success_response("Token verified successfully", {
                'valid': True,
                'user_id': user.id,
                'email': user.email,
                'token_expiry': user.token_expiry.isoformat() if user.token_expiry else None
            })
        except Exception as e:
            _logger.error("Error while verifying the token: %s", e)
            return self._error_response('Server error', 500)
    
    def _success_response(self, message, data, status=200):
        """Formats a success response"""
        response = {
            'success': True,
            'message': message,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        return request.make_response(
            json.dumps(response, default=str),
            status=status,
            headers=[('Content-Type', 'application/json')]
        )
    
    def _error_response(self, message, status=400):
        """Formats an error response"""
        response = {
            'success': False,
            'error': message,
            'timestamp': datetime.now().isoformat()
        }
        return request.make_response(
            json.dumps(response),
            status=status,
            headers=[('Content-Type', 'application/json')]
        )