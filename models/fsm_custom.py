from odoo import models, fields

class FsmCustom(models.Model):

    _inherit = 'project.task'
    distance = fields.Char(string="Distance")
    
