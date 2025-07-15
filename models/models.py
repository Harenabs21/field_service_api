# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class fsm_industry_json_rpc(models.Model):
#     _name = 'fsm_industry_json_rpc.fsm_industry_json_rpc'
#     _description = 'fsm_industry_json_rpc.fsm_industry_json_rpc'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

