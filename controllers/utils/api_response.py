import json
from datetime import datetime
from odoo.http import request


class ApiResponse:

    @staticmethod
    def success_response(message, data, status=200):
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

    @staticmethod
    def error_response(message, data, status=400):
        """Formats an error response"""
        response = {
            'success': False,
            'message': message,
            'data': data or {},
            'timestamp': datetime.now().isoformat()
        }
        return request.make_response(
            json.dumps(response),
            status=status,
            headers=[('Content-Type', 'application/json')]
        )
