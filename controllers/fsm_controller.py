import logging
import datetime
import json
import re
from odoo import http
from odoo.http import request
from .auth_controller import token_required

_logger = logging.getLogger(__name__)

class FSMController(http.Controller):

    @http.route('/api/interventions', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    @token_required
    def get_field_service_tasks(self, **kwargs):
        """
        Retrieve specific user's interventions
        GET /api/interventions?status=<status>&priority=<priority>
        Headers: Authorization: Bearer <token>
        """
        try:
            current_user = request.env.user
            status = kwargs.get('status') 
            priority = kwargs.get('priority')

            domain = [('is_fsm', '=', True), ('user_ids', 'in', current_user.id)]

            if status:
                domain.append(('stage_id.name', '=', status))
            if priority:
                domain.append(('priority', '=', priority))    

            task_model = request.env['project.task'].sudo()
            tasks = task_model.search(domain, order='date_deadline ASC')

            results = []
            for task in tasks:
                results.append({
                    'id': task.id,
                    'title': task.name,
                    'dateStart': task.create_date.isoformat() if task.create_date else None,
                    'dateEnd': task.date_deadline.isoformat() if task.date_deadline else None,
                    'status': task.stage_id.name if task.stage_id else '',
                    'priority': self.map_priority(task.priority),
                    'description': task.description or '',
                    'client': task.partner_id.name if task.partner_id else '',
                    'long': task.partner_id.partner_longitude,
                    'lat': task.partner_id.partner_latitude,
                    'telephone': task.partner_id.phone if task.partner_id else '',
                    'address': re.sub(r'\s+', ' ', task.partner_id.contact_address or '').strip(),
                    'distance': task.distance if hasattr(task, 'distance') else None,
                })

            return self._success_response("Interventions data retrieved successfully",
                                          results)

        except Exception as e:
            _logger.error("Erreur lors de la récupération des tâches: %s", e)
            return self._error_response('Erreur serveur', 500)
        
    @http.route('/api/interventions/<int:task_id>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    @token_required
    def get_field_service_task(self, task_id, **kwargs):
        """
        Retrieve specific intervention owned by user by the task_id
        GET /api/interventions/<taks_id>
        Headers: Authorization: Bearer <token>
        """    
        try:
            current_user = request.env.user
            domain = [('user_ids', 'in', current_user.id), ('id', '=', task_id)]
            task = request.env['project.task'].sudo().search(domain)
            if not task.exists():
                return self._error_response('Tâche non trouvée', 404)
            task_data = {
                    'id': task.id,
                    'title': task.name,
                    'dateStart': task.create_date.isoformat() if task.create_date else None,
                    'dateEnd': task.date_deadline.isoformat() if task.date_deadline else None,
                    'status': task.stage_id.name if task.stage_id else '',
                    'priority': self.map_priority(task.priority),
                    'description': task.description or '',
                    'client': task.partner_id.name if task.partner_id else '',
                    'long': task.partner_id.partner_longitude,
                    'lat': task.partner_id.partner_latitude,
                    'telephone': task.partner_id.phone if task.partner_id else '',
                    'address': re.sub(r'\s+', ' ', task.partner_id.contact_address or '').strip(),
                    'distance': task.distance if hasattr(task, 'distance') else None,
                }
            return self._success_response("task retrieved successfully", task_data)

        except Exception as e:
            _logger.error("Error while retrieving the tasks datas: %s", e)
            return self._error_response('Server error', 500)    
        
    def map_priority(self, priority_value):
        """Mapping task priority"""
        return 'Haute' if priority_value == '1' else 'Normale'    
        
    def _success_response(self, message, data, status=200):
        """Formate une réponse de succès"""
        response = {
            'success': True,
            'message': message,
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