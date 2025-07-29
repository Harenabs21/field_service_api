from odoo import models, fields


class FsmCustom(models.Model):

    _inherit = 'project.task'

    distance = fields.Char(string="Distance")
    customer_signature = fields.Binary(string="Customer Signature")
    customer_signature_filename = fields.Char(string="Signature Filename")
