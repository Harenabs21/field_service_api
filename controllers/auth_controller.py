import functools
import json
import logging

from odoo.http import request
from odoo import http
from .utils.api_response import ApiResponse

_logger = logging.getLogger(__name__)


def token_required(f):
    """Decorator to verify the access token"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.httprequest.headers.get('Authorization')

        if not token:
            return ApiResponse.error_response("Missing token", None, 401)

        try:
            if token.startswith('Bearer '):
                token = token.split(' ')[1]

            user = request.env['res.users'].sudo().search(
                [('access_token', '=', token)],
                limit=1
            )

            if not user or not user.validate_token(token):
                return ApiResponse.error_response("Invalid token", None, 401)

            request.env.user = user

        except Exception as e:
            _logger.error("Error token validation: %s", e)
            return ApiResponse.error_response("Authentication failed", None,
                                              401)

        return f(*args, **kwargs)

    return decorated_function


class AuthController(http.Controller):
    """Authentication controller"""

    @http.route(
        '/api/auth/login', type='http', auth='public',
        methods=['POST'], csrf=False, cors='*'
    )
    def api_login(self):
        """
        User authentication and token generation
        POST /api/auth/login
        Body: {"email": "admin", "password": "admin"}
        """
        try:
            db = request.session.db
            if not db:
                return ApiResponse.error_response(
                    'Database not specified', None, 400
                )
            data = json.loads(
                request.httprequest.data.decode('utf-8')
            )
            email = data.get('email')
            password = data.get('password')
            credentials = {
                'login': email,
                'password': password,
                'type': 'password'
            }

            if not all([db, email, password]):
                return ApiResponse.error_response(
                    'Credentials required', None, 400
                )

            try:
                request.session.authenticate(db, credentials)
                uid = request.session.uid
            except Exception as e:
                _logger.error("Authentication error: %s", e)
                return ApiResponse.error_response(
                    'Authentication error', None, 401
                )

            if not uid:
                return ApiResponse.error_response(
                    'Incorrect credentials', None, 401
                )

            user = request.env['res.users'].sudo().browse(uid)
            token = user.generate_access_token()

            return ApiResponse.success_response(
                "Login successfully",
                {
                    'userId': uid,
                    'email': user.email,
                    'name': user.name,
                    'token': token
                }
            )

        except json.JSONDecodeError:
            return ApiResponse.error_response(
                'Invalid JSON format', None, 400
            )
        except Exception as e:
            _logger.error("Authentication error: %s", e)
            return ApiResponse.error_response(
                'Server error', None, 500
            )

    @http.route(
        '/api/auth/verify-token', type='http', auth='public',
        methods=['GET'], csrf=False, cors='*'
    )
    @token_required
    def verify_token(self):
        """
        Token validation
        GET /api/auth/verify-token
        Headers: Authorization: Bearer <token>
        """
        try:
            user = request.env.user
            return ApiResponse.success_response(
                "Token verified successfully",
                {
                    'valid': True,
                    'user_id': user.id,
                    'email': user.email
                }
            )
        except Exception as e:
            _logger.error("Error while verifying the token: %s", e)
            return ApiResponse.error_response(
                'Server error', None, 500
            )

    @http.route(
            '/api/auth/reset-password', type='http', auth='public',
            methods=['POST'], csrf=False
    )
    def reset_password(self):
        """
        Send an email to reset password
        """
        data = json.loads(
                request.httprequest.data.decode('utf-8')
            )
        login = data.get("email")
        if not login:
            return ApiResponse.error_response("Email required", None, 400)
        user = request.env['res.users'].sudo().search(
            [('login', '=', login)], limit=1
            )
        if not user:
            return ApiResponse.error_response("User not found", None, 404)
        try:
            user.action_reset_password()
            return ApiResponse.success_response(
                "Password reset link sent successfully", {}
                )
        except Exception as e:
            _logger.error("Server error %s", e)
            return ApiResponse.error_response(
                "Failed to send reset password of email", None, 500
                )

    @http.route(
        '/api/auth/logout', type='http', auth='public',
        methods=['POST'], csrf=False, cors='*'
    )
    @token_required
    def api_logout(self):
        """
        Loging out user
        POST /api/auth/logout
        Headers: Authorization: Bearer <token>
        """
        try:
            user = request.env.user
            user.invalidate_token()
            return ApiResponse.success_response(
                "Log out successfully", {}
            )
        except Exception as e:
            _logger.error("Error while logging out: %s", e)
            return ApiResponse.error_response(
                'Server error', None, 500
            )
