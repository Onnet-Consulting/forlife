# -*- coding: utf-8 -*-
# from odoo import http


# class ForlifeReducePermission(http.Controller):
#     @http.route('/forlife_reduce_permission/forlife_reduce_permission', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/forlife_reduce_permission/forlife_reduce_permission/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('forlife_reduce_permission.listing', {
#             'root': '/forlife_reduce_permission/forlife_reduce_permission',
#             'objects': http.request.env['forlife_reduce_permission.forlife_reduce_permission'].search([]),
#         })

#     @http.route('/forlife_reduce_permission/forlife_reduce_permission/objects/<model("forlife_reduce_permission.forlife_reduce_permission"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('forlife_reduce_permission.object', {
#             'object': obj
#         })
