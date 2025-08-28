from odoo import http, _
import logging
from .utils.api_response import ApiResponse

_logger = logging.getLogger(__name__)


class PingController(http.Controller):

    @http.route(
        '/api/ping',
        type='http',
        auth='public',
        methods=['GET', 'HEAD'],
        csrf=False,
        cors='*'
    )
    def ping(self):
        try:
            return ApiResponse.success_response(
                _("Ping Success"), "Pong"
                )
        except Exception as e:
            _logger.exception("Error in /api/ping:", e)
            return ApiResponse.error_response(
                _("Ping Error"), None, status=500
                )
