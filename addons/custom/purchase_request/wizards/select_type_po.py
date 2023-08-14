from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class SelectTypePo(models.TransientModel):
    _name = "select.type.po"
    _description = "Select Type Po"

    type_po = fields.Selection(
        copy=False,
        default='cost',
        string="Loại đơn hàng",
        required=True,
        selection=[
            ('tax', 'Đơn mua hàng nhập khẩu'),
            ('cost', 'Đơn mua hàng nội địa'),
        ])

    def select_type_purchase_order(self):
        for rec in self:
            req_id = self._context.get('active_ids') or self._context.get('active_id')
            current_request = self.env['purchase.request'].search([('id', 'in', req_id)])

            if len(current_request.mapped('account_analytic_id')) > 1 or (current_request.filtered(lambda x: not x.account_analytic_id) and current_request.filtered(lambda x: x.account_analytic_id)):
                raise ValidationError(_('Vui lòng chọn các PR có cùng cấu hình "Trung tâm chi phí"'))

            if len(current_request.mapped('occasion_code_id')) > 1 or (current_request.filtered(lambda x: not x.occasion_code_id) and current_request.filtered(lambda x: x.occasion_code_id)):
                raise ValidationError(_('Vui lòng chọn các PR có cùng cấu hình "Mã vụ việc"'))

            if len(current_request.mapped('production_id')) > 1 or (current_request.filtered(lambda x: not x.production_id) and current_request.filtered(lambda x: x.production_id)):
                raise ValidationError(_('Vui lòng chọn các PR có cùng cấu hình "Lệnh sản xuất"'))

            current_request.write({
                'type_po': rec.type_po,
            })
            current_request.create_purchase_orders()
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

