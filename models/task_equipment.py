from odoo import models, fields


class TaskEquipment(models.Model):

    _name = 'task.equipment'
    _description = 'Task Equipment'

    task_id = fields.Many2one(
        'project.task', string='Task', required=True, ondelete='cascade'
        )
    equipment_id = fields.Many2one(
        'product.product',
        string='Equipment',
        required=True,
        domain=[('type', 'in', ['consu', 'combo'])]
        )
