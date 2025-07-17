import json
import logging
from datetime import datetime
import functools
from odoo import http
from odoo.http import request


_logger = logging.getLogger(__name__)

# ===========================================
# DÉCORATEUR POUR AUTHENTIFICATION PAR TOKEN
# ===========================================


def token_required(f):
    """Décorateur pour vérifier le token d'accès"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.httprequest.headers.get('Authorization')
        
        if not token:
            return request.make_response(
                json.dumps({'success': False, 'error': 'Token manquant'}),
                status=401,
                headers=[('Content-Type', 'application/json')]
            )
        
        try:
            # Extraction du token (format: "Bearer <token>" ou juste "<token>")
            if token.startswith('Bearer '):
                token = token.split(' ')[1]
            
            # Recherche de l'utilisateur par token
            user = request.env['res.users'].sudo().search([
                ('access_token', '=', token)
            ], limit=1)
            
            if not user or not user.validate_token(token):
                return request.make_response(
                    json.dumps({'success': False, 'error': 'Token invalide ou expiré'}),
                    status=401,
                    headers=[('Content-Type', 'application/json')]
                )
            
            # Mise à jour du contexte utilisateur
            request.env.user = user
            
        except Exception as e:
            _logger.error("Erreur validation token: %s", e)
            return request.make_response(
                json.dumps({'success': False, 'error': 'Erreur d\'authentification'}),
                status=401,
                headers=[('Content-Type', 'application/json')]
            )
        
        return f(*args, **kwargs)
    
    return decorated_function

# ===========================================
# CONTROLLER D'AUTHENTIFICATION
# ===========================================


class AuthController(http.Controller):
    """Controller pour les authentifications"""
    @http.route('/api/login', type='http', auth='public', methods=['POST'], csrf=False, cors='*')
    def api_login(self, **kwargs):
        """
        Authentification utilisateur et génération de token
        POST /api/login
        Headers: {'db' : db_name}
        Body: { "login": "admin", "password": "admin"}
        """
        try:
            # Récupération des données JSON
            db = request.httprequest.headers.get('db')
            data = json.loads(request.httprequest.data.decode('utf-8'))
            login = data.get('login')
            password = data.get('password')
            credentials = {'login': login, 'password': password, 'type': 'password'}

            if not all([db, login, password]):
                return self._error_response('db, login et password requis', 400)
            
            # Authentification
            try:
                request.session.authenticate(db, credentials)
                uid = request.session.uid
            except Exception as e:
                _logger.error("Erreur authentification: %s", e)
                return self._error_response('Erreur d\'authentification', 401)
            
            if not uid:
                return self._error_response('Identifiants incorrects', 401)
            
            # Génération du token
            user = request.env['res.users'].sudo().browse(uid)
            token = user.generate_access_token()
            
            return self._success_response("Login successfully",
                        {
                            'user_id': uid,
                            'email': user.email,
                            'token': token
                        })
            
        except json.JSONDecodeError:
            return self._error_response('Format JSON invalide', 400)
        except Exception as e:
            _logger.error("Erreur lors de l'authentification: %s", e)
            return self._error_response('Erreur serveur', 500)
    
    @http.route('/api/logout', type='http', auth='public', methods=['POST'],
                     csrf=False, cors='*')
    @token_required
    def api_logout(self, **kwargs):
        """
        Déconnexion utilisateur
        POST /api/logout
        Headers: Authorization: Bearer <token>
        """
        try:
            user = request.env.user
            user.invalidate_token()
            return self._success_response("Log out successfully",{})
        except Exception as e:
            _logger.error("Erreur lors de la déconnexion: %s", e)
            return self._error_response('Erreur serveur', 500)
    
    @http.route('/api/token/verify', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    @token_required
    def verify_token(self, **kwargs):
        """
        Vérification de la validité du token
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
            _logger.error("Erreur lors de la vérification du token: %s", e)
            return self._error_response('Erreur serveur', 500)
    
    # ===========================================
    # MÉTHODES UTILITAIRES
    # ===========================================
    
    def _success_response(self, message, data, status=200):
        """Formate une réponse de succès"""
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
        """Formate une réponse d'erreur"""
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