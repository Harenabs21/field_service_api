import base64
import json
import logging
import mimetypes
import re

from datetime import datetime
from odoo import http, _
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
                sale_order_lines = request.env[
                    'sale.order.line'].sudo().search([
                        ('task_id', '=', task.id)])

                material_lines = [
                    {
                        'material_id': line.product_id.id,
                        'name': line.product_id.name,
                        'quantity': line.product_uom_qty
                    } for line in sale_order_lines
                ]

                results.append({
                    'id': task.id,
                    'title': task.name,
                    'dateStart': task.planned_date_begin.replace(
                        tzinfo=UTC).isoformat()
                    if task.planned_date_begin else None,
                    'dateEnd': task.date_deadline.replace(
                        tzinfo=UTC).isoformat()
                    if task.date_deadline else None,
                    'status': _(task.stage_id.name) if task.stage_id else '',
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
                    'materials': material_lines
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

            sale_order_lines = request.env['sale.order.line'].sudo().search([
                ('task_id', '=', task.id)
            ])

            material_lines = [
                    {
                        'material_id': line.product_id.id,
                        'name': line.product_id.name,
                        'quantity': line.product_uom_qty
                    } for line in sale_order_lines
                ]

            task_data = {
                'id': task.id,
                'title': task.name,
                'dateStart': task.planned_date_begin.replace(
                    tzinfo=UTC).isoformat()
                if task.planned_date_begin else None,
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
                'materials': material_lines
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

                    timesheet = request.env[
                        'account.analytic.line'].sudo().create(
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

    @http.route(
        '/api/interventions/sync',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
        cors='*'
    )
    @token_required
    def sync_intervention_data(self):
        """
        Synchronize offline intervention data
        - Create timesheet
        - Update task status
        - Upload files
        """
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
            tasks_data = data.get('tasks', [])
            if not tasks_data:
                return ApiResponse.error_response("No tasks provided", 400)

            for task_data in tasks_data:
                task_id = task_data.get('task_id')
                values = task_data.get('values', {})

                task = request.env['project.task'].sudo().browse(task_id)
                if not task.exists() or not task.is_fsm:
                    return ApiResponse.error_response(
                        "Task not found or not a FSM task", 404)

                if request.env.user not in task.user_ids:
                    return ApiResponse.error_response(
                        "You can only sync your own tasks", 403)

                self._update_task_data(task, values)

                attachment_files = values.get('attachment_files', [])
                self._upload_files(task, attachment_files)

                comments = values.get('comments', [])
                self._post_comments(task, comments)

            return ApiResponse.success_response(
                "Intervention synchronized successfully", {})

        except json.JSONDecodeError:
            return ApiResponse.error_response('Invalid JSON format', 400)
        except Exception as e:
            _logger.error("Error in sync: %s", e)
            return ApiResponse.error_response('Server error', 500)

    def _map_priority(self, priority_value):
        """Map task priority"""
        return _('High') if priority_value == '1' else _('Normal')

    def _update_task_data(self, task, values):
        """
        Updates status and adds timesheets
        """
        updates = {}

        new_status = values.get('status')
        if new_status:
            stage = request.env['project.task.type'].sudo().search([
                ('name', '=', new_status),
                ('project_ids', 'in', task.project_id.id)
            ], limit=1)
            if stage:
                updates['stage_id'] = stage.id

        timesheet_entries = values.get('timesheets', [])
        new_timesheet_ids = []

        for entry in timesheet_entries:
            try:
                date = datetime.strptime(entry.get('date'), "%Y-%m-%d").date()
            except (ValueError, TypeError):
                date = datetime.now().date()

            timesheet = request.env['account.analytic.line'].sudo().create({
                'task_id': task.id,
                'project_id': task.project_id.id if task.project_id else None,
                'name': entry.get('description', ''),
                'unit_amount': float(entry.get('time_allocated', 0)),
                'date': date,
                'user_id': request.env.user.id
            })
            new_timesheet_ids.append(timesheet.id)

        if new_timesheet_ids:
            updates['timesheet_ids'] = [(4, tid) for tid in new_timesheet_ids]

        if updates:
            task.sudo().write(updates)

    def _upload_files(self, task, attachment_files):
        """
        Saves base64 encoded files as task-related attachments
        """
        attachment_ids = []
        for file in attachment_files:
            try:
                filename = file.get('filename')
                encoded_data = file.get('data')
                if not filename or not encoded_data:
                    continue

                decoded = base64.b64decode(encoded_data)
                attachment = request.env['ir.attachment'].sudo().create({
                    'name': filename,
                    'datas': base64.b64encode(decoded),
                    'res_model': 'project.task',
                    'res_id': task.id,
                    'mimetype': self._get_mimetype(filename),
                    'type': 'binary'
                })
                attachment_ids.append(attachment.id)
            except Exception as e:
                _logger.warning("File ignored : %s", e)
        return attachment_ids

    def _post_comments(self, task, comments):
        """
        Posts comments to the task
        """
        for comment in comments:
            try:
                message_body = comment.get('message')
                attachment_files = comment.get('attachment_files', [])

                if not message_body:
                    continue

                attachment_ids = self._upload_files(task, attachment_files)

                note_subtype = request.env.ref('mail.mt_note')

                request.env['mail.message'].sudo().create({
                    'body': message_body,
                    'model': 'project.task',
                    'res_id': task.id,
                    'message_type': 'comment',
                    'subtype_id': note_subtype.id if note_subtype else None,
                    'author_id': request.env.user.partner_id.id,
                    'attachment_ids': [(6, 0, attachment_ids)] if
                    attachment_ids else False,
                })

            except Exception as e:
                _logger.warning("Manual comment creation failed: %s", e)

    def _get_mimetype(self, filename):
        """
        Dynamically guess the mimetype from the filename
        """
        mimetype, _ = mimetypes.guess_type(filename)
        return mimetype or 'application/octet-stream'
