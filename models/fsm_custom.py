from odoo import models, fields


class FsmCustom(models.Model):

    _inherit = 'project.task'

    distance = fields.Char(string="Distance")
    client_signature = fields.Binary(string="Client Signature")
    client_signature_filename = fields.Char(string="Signature Filename")
