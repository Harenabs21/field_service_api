from odoo import models, fields


class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'

    stage_sequence = fields.Integer(
        string='Stage Sequence')

    _sql_constraints = [
        ('stage_sequence_unique', 'unique(stage_sequence)',
         'The stage sequence must be unique!'),
    ]
