from unittest.case import _id

from odoo import models, fields, _, api


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _process_order(self, order, draft, existing_order):
        date_order = fields.Datetime.from_string(order['data']['creation_date'].replace('T', ' ')[:19])
        for line in order['data']['lines']:
            for usage in line[2]['promotion_usage_ids']:
                program = self.env['promotion.program'].browse(usage[2].get('program_id'))
                if program.registering_tax and program.tax_from_date <= date_order <= program.tax_to_date:
                    usage[2]['registering_tax'] = True
        order_id = super(PosOrder, self)._process_order(order, draft, existing_order)
        code_ids = []
        partner_id = order['data']['partner_id']
        if partner_id:
            for line in order['data']['lines']:
                code_ids += [usage[2].get('code_id') for usage in line[2]['promotion_usage_ids']]
            if len(code_ids) > 0:
                codes = self.env['promotion.code'].browse(code_ids)
                codes.used_partner_ids |= self.env['res.partner'].browse(partner_id)
        return order_id
