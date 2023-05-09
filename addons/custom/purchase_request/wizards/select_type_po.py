from odoo import fields, models, api

class SelectTypePo(models.TransientModel):
    _name = "select.type.po"
    _description = "Select Type Po"

    type_po = fields.Selection(
        copy=False,
        default='cost',
        string="Loại đơn hàng",
        selection=[('tax', 'Đơn mua hàng nhập khẩu'),
                   ('cost', 'Đơn mua hàng nội địa'),
                   ])

    def select_type_purchase_order(self):
        for rec in self:
            req_id = self._context.get('active_ids') or self._context.get('active_id')
            current_request = self.env['purchase.request'].search([('id', 'in', req_id)])
            for item in current_request:
                if item:
                    item.write({
                        'type_po': rec.type_po,
                    })
                item.create_purchase_orders()
        return {
            'name': 'Purchase Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_id': False,
            'view_mode': 'tree,form',
            'domain': [('type_po_cost', '=',  rec.type_po)],
        }

    def cancel(self):
        pass

