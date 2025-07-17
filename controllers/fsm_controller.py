import logging
import datetime
import json
from odoo import http
from odoo.http import request
from .auth_controller import token_required

_logger = logging.getLogger(__name__)

class FSMController(http.Controller):

    @http.route('/api/field-service/tasks', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    @token_required
    def get_field_service_tasks(self, **kwargs):
        """
        Récupération des tâches Field Service
        GET /api/field-service/tasks?limit=10&offset=0&status=todo
        Headers: Authorization: Bearer <token>
        """
        try:
            current_user = request.env.user
            status = kwargs.get('status')  # Ex: 'todo'

            # Domaine : tâches FSM assignées à l'utilisateur connecté
            domain = [('is_fsm', '=', True), ('user_ids', 'in', current_user.id)]

            if status:
                domain.append(('stage_id.name', '=', status))

            Task = request.env['project.task'].sudo()
            tasks = Task.search(domain, order='date_deadline ASC')

            results = []
            for task in tasks:
                results.append({
                    'id': task.id,
                    'title': task.name,
                    'dateStart': task.date_deadline.isoformat() if task.date_deadline else None,
                    'dateEnd': task.date_end.isoformat() if task.date_end else None,
                    'status': task.stage_id.name if task.stage_id else '',
                    'priority': task.priority,
                    'client': task.partner_id.name if task.partner_id else '',
                    'telephone': task.partner_id.phone if task.partner_id else '',
                    'distance': task.distance if hasattr(task, 'distance') else None,
                })

            return self._success_response({
                'tasks': results,
                'total': len(results)
            })

        except Exception as e:
            _logger.error("Erreur lors de la récupération des tâches: %s", e)
            return self._error_response('Erreur serveur', 500)
        
    def _success_response(self, data, status=200):
        """Formate une réponse de succès"""
        response = {
            'success': True,
            'data': data,
            'timestamp': datetime.datetime.now().isoformat()
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
            'timestamp': datetime.datetime.now().isoformat()
        }
        return request.make_response(
            json.dumps(response),
            status=status,
            headers=[('Content-Type', 'application/json')]
        )    