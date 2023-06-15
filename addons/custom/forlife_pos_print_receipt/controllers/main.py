# -*- coding: utf-8 -*-

from odoo import api, http
from odoo.http import request
from werkzeug.utils import redirect


class PoitCompensateController(http.Controller):

    @http.route('/pos/point/compensate', type='http', auth="none", methods=['GET'])
    def get_website_translations(self, order_reference=None, redirect_url=None):
        PosOrder = request.env['pos.order'].sudo()
        CompensatePointRequest = request.env['point.compensate.request'].sudo()
        order = PosOrder.search([('name', '=', order_reference)], limit=1)
        redirect_url = redirect_url or "https://format.com.vn/"
        if order:
            CompensatePointRequest.create({'order_id': order.id})
        return redirect(redirect_url)
