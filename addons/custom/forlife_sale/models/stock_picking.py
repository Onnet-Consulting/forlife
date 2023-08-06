from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def confirm_from_so(self, condition=None):
        if condition:
            for move in self.move_ids:
                move.check_quantity()
            self.action_confirm()
            self.move_ids._set_quantities_to_reservation()
            self.with_context(skip_immediate=True).button_validate()
        else:
            self.action_confirm()

    def write(self, vals):
        res = super(StockPicking, self).write(vals)
        if vals.get('note'):
            account_id = self.env['account.move'].search([('stock_move_id', 'in', self.move_ids.ids)])
            account_id.update({'narration': self.note})
        return res

    def create_invoice_out_refund(self):
        if not self:
            return
        invoice_line_ids = []
        promotion_ids = []
        sale_order = self.sale_id

        for line in self.move_ids:
            if self.sale_id.x_origin and self.sale_id.x_origin.promotion_ids:
                promotion_id = self.sale_id.x_origin.promotion_ids.filtered(lambda x: x.product_id.id == line.product_id.id)
                if promotion_id and promotion_id.product_uom_qty:
                    promotion_ids.append((0, 0, {
                        "product_id": promotion_id.product_id.id,
                        "value": - (promotion_id.value / promotion_id.product_uom_qty) * line.quantity_done,
                        "promotion_type": promotion_id.promotion_type,
                        "account_id": promotion_id.account_id.id,
                        "analytic_account_id": promotion_id.analytic_account_id.id,
                        "description": promotion_id.description,
                    }))
            invoice_line = {
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'description': line.product_id.default_code,
                'type': line.product_type,
                'quantity_purchased': line.product_uom_qty,
                'exchange_quantity': 1,
                'product_uom_id': line.product_id.uom_id.id,
                'quantity': line.product_qty,
                'request_code': line.picking_id.name,
                'vendor_price': line.sale_line_id.price_unit,
                'price_unit': line.sale_line_id.price_unit,
                'warehouse': line.location_id.id,
                'tax_ids': [(6, 0, line.sale_line_id.tax_id.ids)],
                'discount': line.sale_line_id.discount,
                'account_analytic_id': line.account_analytic_id.id,
                'work_order': line.sale_line_id.x_manufacture_order_code_id.id,
                'sale_line_ids': [(4, line.sale_line_id.id)]
            }
            invoice_line_ids.append((0, 0, invoice_line))
        vals = {
            'partner_id': self[0].partner_id.id,
            'move_type': 'out_refund',
            'invoice_line_ids': invoice_line_ids,
            'promotion_ids': promotion_ids,
            'invoice_origin': line.sale_line_id.order_id.name,
        }
        if line.sale_line_id.order_id.source_record:
            vals['company_id'] = line.sale_line_id.order_id.company_id.id

        invoice_id = self.env['account.move'].sudo().create(vals)
        for line in invoice_id.invoice_line_ids:
            if line.product_id:
                if self.sale_source_record:
                    res_id = f"product.category,{line.product_id.product_tmpl_id.categ_id.id}"
                    ir_property = self.env['ir.property'].sudo().search([
                        ('name', '=', 'x_property_account_return_id'),
                        ('res_id', '=', res_id),
                        ('company_id', '=', sale_order.company_id.id)
                    ],limit=1)
                    if ir_property:
                        account_id = str(ir_property.value_reference).replace("account.account,", "")
                        line.account_id = self.env['account.account'].sudo().search([('id', '=', account_id)], limit=1)
                    else:
                        line.account_id = line.product_id.product_tmpl_id.categ_id.x_property_account_return_id
                else:
                    line.account_id = line.product_id.product_tmpl_id.categ_id.x_property_account_return_id
        return invoice_id.id

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        if self.picking_type_id.x_is_return:
            for move in self.move_ids:
                account_move = self.env['account.move'].search([('stock_move_id', '=', move.id)])
                account_move_line = account_move.line_ids.filtered(lambda line: line.debit > 0)
                account_id = move.product_id.product_tmpl_id.categ_id.x_property_account_return_id
                if not account_id:
                    raise UserError(_('Bạn chưa cấu hình "Tài khoản trả hàng" trong danh mục sản phẩm của sản phẩm %s') % move.product_id.name)
                account_move_line.account_id = account_id

        # Trường hợp xuất bán thành phẩm hoặc NVL theo LSX từ SO
        for picking_id in self.filtered(lambda x: x.sale_id and x.sale_id.x_manufacture_order_code_id):
            self.update_quantity_production_order(picking_id)

        try:
            sale_from_nhanh = self.sale_id and self.sale_id.source_record
            if self.state == "done" and self.picking_type_code == "outgoing" and sale_from_nhanh:
                picking_out = self.sale_id.picking_ids.filtered(
                    lambda r: r.picking_type_id == self.sale_id.warehouse_id.out_type_id
                )
                picking_out_done = self.sale_id.picking_ids.filtered(
                    lambda r: r.picking_type_id == self.sale_id.warehouse_id.out_type_id and r.state == "done"
                )
                if len(picking_out_done) == len(picking_out):
                    advance_payment = self.env['sale.advance.payment.inv'].create({
                        'sale_order_ids': [(6, 0, self.sale_id.ids)],
                        'advance_payment_method': 'delivered',
                        'deduct_down_payments': True
                    })
                    invoice_id = advance_payment._create_invoices(advance_payment.sale_order_ids)
                    invoice_id.action_post()
            if self.state == "done" and sale_from_nhanh and self.sale_id.x_is_return:
                if self.company_id.id == self.sale_id.company_id.id:
                    self.create_invoice_out_refund()
        except Exception as e:
            pass
        
        return res

    def update_quantity_production_order(self, picking_id):
        """
            Update lại số lượng tồn kho theo LSX ở phiếu nhập xuất bán SO
        """

        for rec in picking_id.move_ids_without_package.filtered(lambda r: r.work_production):
            domain = [('product_id', '=', rec.product_id.id), ('location_id', '=', picking_id.location_id.id), ('production_id', '=', rec.work_production.id)]
            quantity_prodution = self.env['quantity.production.order'].search(domain)
            if quantity_prodution:
                quantity = quantity_prodution.quantity - rec.quantity_done
                if quantity < 0:
                    raise ValidationError('Số lượng tồn kho sản phẩm %s trong lệnh sản xuất %s không đủ để điều chuyển!' % (rec.product_id.display_name, rec.work_production.code))
                else:
                    quantity_prodution.update({
                        'quantity': quantity
                    })
            else:
                raise ValidationError('Sản phẩm %s không có trong lệnh sản xuất %s!' % (rec.product_id.display_name, rec.work_production.code))