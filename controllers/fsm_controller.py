import base64
from datetime import datetime
import json
import logging
from pytz import UTC
import re

from odoo import http
from odoo.http import request
from odoo.tools import html2plaintext
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
                material_lines = self._get_material_lines(task)

                results.append({
                    'id': task.id,
                    'title': task.name,
                    'dateStart': task.planned_date_begin.astimezone(
                        UTC).strftime('%d/%m/%Y')
                    if task.planned_date_begin else None,
                    'dateEnd': task.date_deadline.astimezone(
                        UTC).strftime('%d/%m/%Y')
                    if task.date_deadline else None,
                    'status': task.stage_id.stage_sequence if task.stage_id
                    else None,
                    'priority': task.priority if task.priority else '',
                    'description': html2plaintext(task.description or ''),
                    'customer': task.partner_id.name if task.partner_id
                    else '',
                    'long': task.partner_id.partner_longitude,
                    'lat': task.partner_id.partner_latitude,
                    'telephone': task.partner_id.phone
                    if task.partner_id.phone else '',
                    'address': re.sub(
                        r'\s+', ' ',
                        task.partner_id.contact_address or ''
                    ).strip(),
                    'distance': task.distance if task.distance else 0,
                    'materials': material_lines
                })

            return ApiResponse.success_response(
                "Interventions data retrieved successfully",
                results
            )

        except Exception as e:
            _logger.error("Error while retrieving task data: %s", e)
            return ApiResponse.error_response('Server error',  None, 500)

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
                                                  None, 404
                                                  )

            if current_user not in task.user_ids:
                return ApiResponse.error_response(
                      'You can only view your own task', None, 403
                    )

            material_lines = self._get_material_lines(task)

            task_data = {
                'id': task.id,
                'title': task.name,
                'dateStart': task.planned_date_begin.astimezone(
                    UTC).strftime('%d/%m/%Y')
                if task.planned_date_begin else None,
                'dateEnd': task.date_deadline.astimezone(
                    UTC).strftime('%d/%m/%Y')
                if task.date_deadline else None,
                'status': task.stage_id.stage_sequence if task.stage_id
                else None,
                'priority': task.priority if task.priority else '',
                'description': html2plaintext(task.description or ''),
                'customer': task.partner_id.name if task.partner_id else '',
                'long': task.partner_id.partner_longitude,
                'lat': task.partner_id.partner_latitude,
                'telephone': task.partner_id.phone
                if task.partner_id.phone else '',
                'address': re.sub(
                    r'\s+', ' ',
                    task.partner_id.contact_address or ''
                ).strip(),
                'distance': task.distance if task.distance else 0,
                'materials': material_lines
            }

            return ApiResponse.success_response(
                "Task retrieved successfully", task_data
            )

        except Exception as e:
            _logger.error("Error retrieving task: %s", e)
            return ApiResponse.error_response('Server error',  None, 500)

    @http.route(
        '/api/interventions/update-status',
        type='http',
        auth='public',
        methods=['PUT'],
        csrf=False,
        cors='*'
    )
    @token_required
    def update_task_status(self):
        """
        Update task status
        PUT /api/interventions/update-status
        Headers: Authorization: Bearer <token>
        Body: {
            statusId: <stage_id>,
            interventionId: <task_id>
        }
        """
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
            stage_id = data.get('statusId')
            intervention_id = data.get('interventionId')

            if not stage_id and not intervention_id:
                return ApiResponse.error_response(
                      'stageId or interventionId required', None, 400
                )

            task = request.env['project.task'].sudo().browse(intervention_id)

            if not task or not task.is_fsm:
                return ApiResponse.error_response(
                      'Task not found or not a FSM task', None, 404
                )

            if request.env.user not in task.user_ids:
                return ApiResponse.error_response(
                      'You can only edit your own tasks', None, 403
                )

            status = request.env['project.task.type'].sudo().browse(
                stage_id
                )

            if not status:
                return ApiResponse.error_response('Invalid stage', None, 400)

            task.write({'stage_id': status.id})

            return ApiResponse.success_response("Status updated successfully",
                                                None
                                                )

        except json.JSONDecodeError:
            return ApiResponse.error_response('Invalid JSON format', None, 400)
        except Exception as e:
            _logger.error("Error updating status: %s", e)
            return ApiResponse.error_response('Server error',  None, 500)

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
                      'FSM task not found', None, 404)
            elif request.env.user not in task.user_ids:
                response = ApiResponse.error_response(
                    'You can only create timesheets for your own tasks', None,
                    403
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
                      'Invalid date format. Use YYYY-MM-DD.', None, 400
                    )
        except json.JSONDecodeError:
            response = ApiResponse.error_response('Invalid JSON format', None,
                                                  400)
        except Exception as e:
            _logger.error("Error while creating timesheet: %s", e)
            response = ApiResponse.error_response('Server error', None, 500)

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
            tasks_data = data.get('data', [])
            if not tasks_data:
                return ApiResponse.error_response("No tasks provided", None,
                                                  400)

            for task_data in tasks_data:
                task_id = task_data.get('id')

                task = request.env['project.task'].sudo().browse(task_id)
                if not task.exists() or not task.is_fsm:
                    return ApiResponse.error_response(
                          "Task not found or not a FSM task", None, 404)

                if request.env.user not in task.user_ids:
                    return ApiResponse.error_response(
                          "You can only sync your own tasks", None, 403)

                status = task_data.get('status')
                timesheets = task_data.get('timesheets', [])

                self._update_task_data(task, status, timesheets)

                images = task_data.get('images', [])
                self._upload_files(task, images)

                documents = task_data.get('documents', [])
                self._upload_files(task, documents)

                comments = task_data.get('comments', [])
                self._post_comments(task, comments)

                signature = task_data.get('signature')
                if signature:
                    self._upload_signature(task, signature)

                products = task_data.get('materials', [])
                self._sync_products(task, products)

                sync_response = [
                    {
                        'id': task.id,
                        'title': task.name
                    }
                ]

            return ApiResponse.success_response(
                "Intervention synchronized successfully", sync_response)

        except json.JSONDecodeError:
            return ApiResponse.error_response('Invalid JSON format', None, 400)
        except Exception as e:
            _logger.error("Error in sync: %s", e)
            return ApiResponse.error_response('Server error', None, 500)

    def _update_task_data(self, task, status=None, timesheets=None):
        """
        Updates status and adds timesheets
        """
        updates = {}

        new_status = status
        if new_status:
            stage = request.env['project.task.type'].sudo().search([
                ('name', '=', new_status),
                ('project_ids', 'in', task.project_id.id)
            ], limit=1)
            if stage:
                updates['stage_id'] = stage.id

        timesheet_entries = timesheets or []
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
                'unit_amount': float(entry.get('timeAllocated', 0)),
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
                attachment_files = comment.get('attachmentFiles', [])
                date_str = comment.get('dateCreated',
                                       datetime.now().isoformat())
                date_to_format = date_str.split('.')[0].replace(
                    'T', ' ')
                dateCreated = datetime.strptime(date_to_format,
                                                "%Y-%m-%d %H:%M:%S")

                if not message_body:
                    continue

                attachment_ids = self._upload_files(task, attachment_files)

                note_subtype = request.env.ref('mail.mt_note')

                request.env['mail.message'].sudo().create({
                    'body': message_body,
                    'model': 'project.task',
                    'date': dateCreated,
                    'res_id': task.id,
                    'message_type': 'comment',
                    'subtype_id': note_subtype.id if note_subtype else None,
                    'author_id': request.env.user.partner_id.id,
                    'attachment_ids': [(6, 0, attachment_ids)] if
                    attachment_ids else False,
                })

            except Exception as e:
                _logger.warning("Manual comment creation failed: %s", e)

    def _upload_signature(self, task, signature):
        """
        Upload and save customer signature
        """
        try:
            filename = signature.get('filename')
            encoded_data = signature.get('data')

            if not filename or not encoded_data:
                return

            decoded = base64.b64decode(encoded_data)

            task.write({
                'customer_signature': base64.b64encode(decoded),
                'customer_signature_filename': filename
            })
        except Exception as e:
            _logger.warning("Failed to save signature: %s", e)

    def _get_material_lines(self, task):
        """
        Retrieve material lines for the task
        """
        sale_order_lines = request.env['sale.order.line'].sudo().search([
                ('task_id', '=', task.id),
                ('product_uom_qty', '>', 0)
            ])

        material_lines = [
                {
                    'id': line.product_id.id,
                    'name': line.product_id.name,
                    'quantity': line.product_uom_qty
                } for line in sale_order_lines
            ]

        return material_lines

    def _sync_products(self, task, products):
        """
        Synchronize equipment (products) linked to an intervention (Task)
        - Updates the quantity if the product already exists
        - Creates a line if the product is not yet linked
        - Creates the product if it does not exist in DB
        - Quantity 0 means keep the line but no deletion
        """
        sale_order_line = request.env['sale.order.line'].sudo()
        product_model = request.env['product.product'].sudo()
        product_tmpl_model = request.env['product.template'].sudo()

        existing_lines = sale_order_line.search([('task_id', '=', task.id)])
        existing_map = {line.product_id.id: line for line in existing_lines}

        for product in products:
            quantity = float(product.get('quantity', 0))
            product_id = product.get('id')
            name = product.get('name')

            product = None

            if product_id:
                product = product_model.browse(product_id)
                if not product.exists():
                    product = None

            if not product and name:
                product = product_model.search([('name', '=', name)], limit=1)

            if not product and name:
                tmpl = product_tmpl_model.create({
                    'name': name,
                    'type': 'consu',
                    'list_price': 0.0,
                    'uom_id': request.env.ref('uom.product_uom_unit').id,
                    'uom_po_id': request.env.ref('uom.product_uom_unit').id
                })
                product = tmpl.product_variant_id

            if not product:
                continue

            existing_line = existing_map.get(product.id)

            if existing_line:
                existing_line.write({
                    'product_uom_qty': quantity
                })
            else:
                if quantity > 0:
                    request.env['sale.order.line'].sudo().create({
                        'task_id': task.id,
                        'order_id': task.sale_order_id.id,
                        'product_id': product.id,
                        'product_uom_qty': quantity,
                        'product_uom': product.uom_id.id,
                        'price_unit': product.lst_price,
                        'name': product.name,
                    })
