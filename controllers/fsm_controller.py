import logging
import datetime
import json
import re
from odoo import http
from odoo.http import request
from odoo.tools import html2plaintext
from .auth_controller import token_required

_logger = logging.getLogger(__name__)


class FSMController(http.Controller):
    """Fiels service controller"""

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
                    'description': html2plaintext(task.description or ''),
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
            _logger.error("Error while retrieving task data: %s", e)
            return self._error_response('Server error', 500)
       
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
                return self._error_response('Intervention not found', 404)
            task_data = {
                    'id': task.id,
                    'title': task.name,
                    'dateStart': task.create_date.isoformat() if task.create_date else None,
                    'dateEnd': task.date_deadline.isoformat() if task.date_deadline else None,
                    'status': task.stage_id.name if task.stage_id else '',
                    'priority': self.map_priority(task.priority),
                    'description': html2plaintext(task.description or ''),
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
        
    @http.route('/api/interventions/<int:task_id>/status', type='http', auth='public', methods=['PUT'], csrf=False, cors='*')
    @token_required
    def update_task_status(self, task_id, **kwargs):
        """
        Updating the status of a task
        PUT /api/interventions/<task_id>/status
        Headers: Authorization: Bearer <token>
        """    
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
            stage_id = data.get('status_id')
            stage_name = data.get('status_name')
            
            if not stage_id and not stage_name:
                return self._error_response('stage_id or stage_name required', 400)
            
            task = request.env['project.task'].sudo().browse(task_id)
            
            if not task or not task.is_fsm:
                return self._error_response('Task not found or not a FSM task', 404)
            
            if request.env.user not in task.user_ids:
                return self._error_response('You can only edit your own tasks', 403)
            
            if stage_id:
                stage = request.env['project.task.type'].sudo().browse(stage_id)
            else:
                stage = request.env['project.task.type'].sudo().search([
                    ('name', '=', stage_name),
                    ('project_ids', 'in', task.project_id.id)
                ], limit=1)
            
            if not stage:
                return self._error_response('Invalid stage', 400)
            
            task.write({'stage_id': stage.id})
            
            return self._success_response("Status updated successfully", {
                'status_id': stage.id,
                'status_name': stage.name
            })
            
        except json.JSONDecodeError:
            return self._error_response('JSON format invalid', 400)
        except Exception as e:
            _logger.error("Error while updating the status: %s", e)
            return self._error_response('Server error', 500)
        
    def map_priority(self, priority_value):
        """Mapping task priority"""
        return 'Haute' if priority_value == '1' else 'Normale'    
        
    def _success_response(self, message, data, status=200):
        """Formats a success response"""
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
        """Formats an error response"""
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