import json
import logging
import re

from datetime import datetime
from odoo import http
from odoo.http import request
from odoo.tools import html2plaintext
from pytz import UTC
from .auth_controller import token_required
from .utils.api_response import ApiResponse

_logger = logging.getLogger(__name__)


class FSMController(http.Controller):
    """Field service controller"""

    @http.route(
        '/api/interventions/list',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
        cors='*'
    )
    @token_required
    def get_field_service_tasks(self, **kwargs):
        """
        Retrieve specific user's interventions
        GET /api/interventions/list?status=<status>&priority=<priority>
        Headers: Authorization: Bearer <token>
        """
        try:
            current_user = request.env.user
            status = kwargs.get('status')
            priority = kwargs.get('priority')

            domain = [
                ('is_fsm', '=', True),
                ('user_ids', 'in', current_user.id)
            ]

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
                    'dateStart': task.date_assign.replace(
                        tzinfo=UTC).isoformat()
                    if task.date_assign else None,
                    'dateEnd': task.date_deadline.replace(
                        tzinfo=UTC).isoformat()
                    if task.date_deadline else None,
                    'status': task.stage_id.name if task.stage_id else '',
                    'priority': self._map_priority(task.priority),
                    'description': html2plaintext(task.description or ''),
                    'client': task.partner_id.name if task.partner_id else '',
                    'long': task.partner_id.partner_longitude,
                    'lat': task.partner_id.partner_latitude,
                    'telephone': task.partner_id.phone
                    if task.partner_id else '',
                    'address': re.sub(
                        r'\s+', ' ',
                        task.partner_id.contact_address or ''
                    ).strip(),
                    'distance': task.distance
                    if hasattr(task, 'distance') else None,
                })

            return ApiResponse.success_response(
                "Interventions data retrieved successfully",
                results
            )

        except Exception as e:
            _logger.error("Error while retrieving task data: %s", e)
            return ApiResponse.error_response('Server error', 500)

    @http.route(
        '/api/interventions/<int:task_id>',
        type='http',
        auth='public',
        methods=['GET'],
        csrf=False,
        cors='*'
    )
    @token_required
    def get_field_service_task(self, task_id):
        """
        Retrieve specific intervention by ID
        GET /api/interventions/<task_id>
        Headers: Authorization: Bearer <token>
        """
        try:
            current_user = request.env.user
            domain = [
                ('user_ids', 'in', current_user.id),
                ('id', '=', task_id)
            ]
            task = request.env['project.task'].sudo().search(domain)
            if not task.exists():
                return ApiResponse.error_response('Intervention not found',
                                                  404
                                                  )

            if current_user not in task.user_ids:
                return ApiResponse.error_response(
                    'You can only view your own task', 403
                    )

            task_data = {
                'id': task.id,
                'title': task.name,
                'dateStart': task.date_assign.replace(tzinfo=UTC).isoformat()
                if task.date_assign else None,
                'dateEnd': task.date_deadline.replace(tzinfo=UTC).isoformat()
                if task.date_deadline else None,
                'status': task.stage_id.name if task.stage_id else '',
                'priority': self._map_priority(task.priority),
                'description': html2plaintext(task.description or ''),
                'client': task.partner_id.name if task.partner_id else '',
                'long': task.partner_id.partner_longitude,
                'lat': task.partner_id.partner_latitude,
                'telephone': task.partner_id.phone if task.partner_id else '',
                'address': re.sub(
                    r'\s+', ' ',
                    task.partner_id.contact_address or ''
                ).strip(),
                'distance': task.distance
                if hasattr(task, 'distance') else None,
            }

            return ApiResponse.success_response(
                "Task retrieved successfully", task_data
            )

        except Exception as e:
            _logger.error("Error retrieving task: %s", e)
            return ApiResponse.error_response('Server error', 500)

    @http.route(
        '/api/interventions/<int:task_id>/update-status',
        type='http',
        auth='public',
        methods=['PUT'],
        csrf=False,
        cors='*'
    )
    @token_required
    def update_task_status(self, task_id):
        """
        Update task status
        PUT /api/interventions/<task_id>/update-status
        Headers: Authorization: Bearer <token>
        """
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
            stage_id = data.get('status_id')
            stage_name = data.get('status_name')

            if not stage_id and not stage_name:
                return ApiResponse.error_response(
                    'stage_id or stage_name required', 400
                )

            task = request.env['project.task'].sudo().browse(task_id)

            if not task or not task.is_fsm:
                return ApiResponse.error_response(
                    'Task not found or not a FSM task', 404
                )

            if request.env.user not in task.user_ids:
                return ApiResponse.error_response(
                    'You can only edit your own tasks', 403
                )

            if stage_id:
                stage = request.env['project.task.type'].sudo().browse(
                    stage_id
                    )
            else:
                stage = request.env['project.task.type'].sudo().search([
                    ('name', '=', stage_name),
                    ('project_ids', 'in', task.project_id.id)
                ], limit=1)

            if not stage:
                return ApiResponse.error_response('Invalid stage', 400)

            task.write({'stage_id': stage.id})
            task_response = {
                'status_id': stage.id,
                'status_name': stage.name
            }

            return ApiResponse.success_response("Status updated successfully",
                                                task_response
                                                )

        except json.JSONDecodeError:
            return ApiResponse.error_response('Invalid JSON format', 400)
        except Exception as e:
            _logger.error("Error updating status: %s", e)
            return ApiResponse.error_response('Server error', 500)

    @http.route(
        '/api/interventions/<int:task_id>/create-timesheet',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
        cors='*'
    )
    @token_required 
    def create_timesheet(self, task_id):
        """
        Create a timesheet entry
        POST /api/interventions/<task_id>/create-timesheet
        Headers: Authorization: Bearer <token>
        Body: {
            "description": "Work done",
            "unit_amount": 2.5,
            "date": "2024-01-15"
        }
        """
        response = None
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))

            task = request.env['project.task'].sudo().browse(task_id)

            if not task.exists() or not task.is_fsm:
                response = ApiResponse.error_response(
                    'FSM task not found', 404)
            elif request.env.user not in task.user_ids:
                response = ApiResponse.error_response(
                    'You can only create timesheets for your own tasks', 403
                )
            else:
                date_str = data.get('date')
                try:
                    date = (
                        datetime.strptime(date_str, "%Y-%m-%d").date()
                        if date_str else datetime.now().date()
                    )

                    timesheet_data = {
                        'task_id': task_id,
                        'project_id': (
                            task.project_id.id if task.project_id else None
                        ),
                        'name': data.get('description', ''),
                        'unit_amount': float(data.get('time_allocated', 0)),
                        'date': date,
                        'user_id': request.env.user.id
                    }

                    timesheet = request.env['account.analytic.line'].sudo().create(
                        timesheet_data
                    )

                    timesheet_response = {
                        'id': timesheet.id,
                        'description': timesheet.name,
                        'date': timesheet.date.replace(tzinfo=UTC).isoformat(),
                        'time_allocated': timesheet.unit_amount
                    }

                    response = ApiResponse.success_response(
                        "Timesheet created successfully",
                        timesheet_response
                    )
                except ValueError:
                    response = ApiResponse.error_response(
                        'Invalid date format. Use YYYY-MM-DD.', 400
                    )
        except json.JSONDecodeError:
            response = ApiResponse.error_response('Invalid JSON format', 400)
        except Exception as e:
            _logger.error("Error while creating timesheet: %s", e)
            response = ApiResponse.error_response('Server error', 500)

        return response

    def _map_priority(self, priority_value):
        """Map task priority"""
        return 'Haute' if priority_value == '1' else 'Normale'
