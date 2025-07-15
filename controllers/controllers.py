# -*- coding: utf-8 -*-
# from odoo import http


# class FsmIndustryJsonRpc(http.Controller):
#     @http.route('/fsm_industry_json_rpc/fsm_industry_json_rpc', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/fsm_industry_json_rpc/fsm_industry_json_rpc/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('fsm_industry_json_rpc.listing', {
#             'root': '/fsm_industry_json_rpc/fsm_industry_json_rpc',
#             'objects': http.request.env['fsm_industry_json_rpc.fsm_industry_json_rpc'].search([]),
#         })

#     @http.route('/fsm_industry_json_rpc/fsm_industry_json_rpc/objects/<model("fsm_industry_json_rpc.fsm_industry_json_rpc"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('fsm_industry_json_rpc.object', {
#             'object': obj
#         })

