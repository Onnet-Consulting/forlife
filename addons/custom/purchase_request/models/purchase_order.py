from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date
import json


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    request_id = fields.Many2one('purchase.request')
    purchase_request_ids = fields.Many2many('purchase.request')
    partner_id = fields.Many2one('res.partner', required=False)
    production_id = fields.Many2many('forlife.production', string='Production Order', domain=[('state', '=', 'approved'), ('status', '!=', 'done')], copy=False)
    event_id = fields.Many2one('forlife.event', string='Event Program')
    has_contract_commerce = fields.Boolean(string='Có hóa đơn hay không?')
    rejection_reason = fields.Text()
    is_check_line_material_line = fields.Boolean(compute='_compute_order_line_production_order')
    # approval_logs_ids = fields.One2many('approval.logs', 'purchase_order_id')
    order_line_production_order = fields.Many2many('purchase.order.line',
                                                  compute='_compute_order_line_production_order',
                                                  inverse='_inverse_order_line_production_order')

    @api.depends('order_line.product_id', 'order_line')
    def _compute_order_line_production_order(self):
        self = self.sudo()  # tối ưu tốc độ ghi dữ liệu
        product_in_production_order = self.env['production.order'].search([('type', '=', 'normal')]).mapped('product_id')
        for rec in self:
            order_line_production_order = rec.order_line.filtered(lambda r: r.product_id.id in product_in_production_order.ids)
            rec.order_line_production_order = order_line_production_order.ids
            if not order_line_production_order or not rec.order_line:
                rec.is_check_line_material_line = True
            else:
                rec.is_check_line_material_line = False

    def _inverse_order_line_production_order(self):
        pass

    @api.onchange('order_line_production_order')
    def _onchange_order_line_production_order(self):
        pass

    def action_approved(self):
        for rec in self:
            for line in rec.order_line:
                if not line.purchase_request_line_id:
                    continue
                purchase_request_line = line.purchase_request_line_id
                purchase_request_name = purchase_request_line.request_id.name
                # if (line.product_qty + purchase_request_line.order_quantity) > purchase_request_line.purchase_quantity:
                #     raise ValidationError('Số lượng sản phẩm %s còn lại không đủ!\nVui lòng check mã phiếu yêu cầu %s.' % (line.product_id.name, purchase_request_name))
        res = super(PurchaseOrder, self).action_approved()
        for rec in self:
            material_data = []
            for line in rec.order_line:
                product = line.product_id
                production_order = rec.env['production.order'].search([('product_id', '=', product.id), ('type', '=', 'normal')], limit=1)
                if not production_order:
                    continue
                production_data = []
                for production_line in production_order.order_line_ids:
                    production_data.append((0, 0, {
                        'product_id': production_line.product_id.id,
                        'product_qty': line.product_qty / production_order.product_qty * production_line.product_qty,
                    }))
                material_data.append((0, 0, {
                    'purchase_order_line_id': line.id,
                    'product_id': product.id,
                    'free_good': line.free_good,
                    'purchase_quantity': line.purchase_quantity,
                    'purchase_uom': line.purchase_uom.id,
                    'exchange_quantity': line.exchange_quantity,
                    'product_qty': line.product_qty,
                    'purchase_material_line_item_ids': production_data,
                }))
            rec.env['purchase.material'].create({
                'source_document': rec.name,
                'purchase_material_line_ids': material_data,
            })
        for rec in self:
            for item in rec.order_line:
                production_order = self.env['production.order'].search(
                    [('product_id', '=', item.product_id.id), ('type', '=', 'normal')], limit=1)
                if not item.purchase_order_line_material_line_ids:
                    for production_line in production_order.order_line_ids:
                        self.env['purchase.order.line.material.line'].create({
                            'purchase_order_line_id': item.id,
                            'product_id': production_line.product_id.id,
                            'uom': production_line.uom_id.id,
                            'production_order_product_qty': production_order.product_qty,
                            'production_line_product_qty': production_line.product_qty,
                            'price_unit': production_line.price,
                            'is_from_po': True,
                        })
        return res


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    state = fields.Selection(related='order_id.state', store=1)
    purchase_request_line_id = fields.Many2one('purchase.request.line', ondelete='cascade')
    purchase_order_line_material_line_ids = fields.One2many('purchase.order.line.material.line',
                                                            'purchase_order_line_id')
    product_type = fields.Selection(related='product_id.product_type', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', change_default=True, index='btree_not_null')

    @api.constrains('taxes_id')
    def _check_taxes_id(self):
        for line in self:
            if len(line.taxes_id) > 1:
                raise ValidationError('Only one tax can be applied to a purchase order line.')

    def action_npl(self):
        self.ensure_one()
        if not self.purchase_order_line_material_line_ids:
            product = self.product_id
            production_order = self.env['production.order'].search(
                [('product_id', '=', product.id), ('type', '=', 'normal')], limit=1)
            if not production_order:
                raise ValidationError('Sản phẩm không hợp lệ, vui lòng kiểm tra lại!')
            production_data = []
            for production_line in production_order.order_line_ids:
                product_plan_qty = self.product_qty / production_order.product_qty * production_line.product_qty
                production_data.append((0, 0, {
                    'product_id': production_line.product_id.id,
                    'uom': production_line.uom_id.id,
                    # 'product_qty': product_plan_qty,
                    'production_order_product_qty': production_order.product_qty,
                    'production_line_product_qty': production_line.product_qty,
                    'production_line_price_unit': production_line.price,
                    'price_unit': production_line.price if production_line.product_id.product_tmpl_id.x_type_cost_product else 0,
                    'is_from_po': True,
                }))
            self.write({
                'purchase_order_line_material_line_ids': production_data
            })
        else:
            product = self.product_id
            production_order = self.env['production.order'].search(
                [('product_id', '=', product.id), ('type', '=', 'normal')], limit=1)
            if not production_order:
                raise ValidationError('Sản phẩm không hợp lệ, vui lòng kiểm tra lại!')
            for production_line in production_order.order_line_ids:
                for item in self.purchase_order_line_material_line_ids:
                    item.write({'product_qty': item.purchase_order_line_id.product_qty * production_line.product_qty
                                })
        view_id = self.env.ref('purchase_request.purchase_order_line_material_form_view').id
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_type': 'form',
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'target': 'new',
            'res_id': self.id,
            'context': dict(self._context),
        }


class PurchaseOrderLineMaterialLine(models.Model):
    _name = 'purchase.order.line.material.line'
    _description = 'Purchase Order Line Material Line'

    purchase_order_line_id = fields.Many2one('purchase.order.line', ondelete='cascade')

    product_id = fields.Many2one('product.product')
    name = fields.Char(related='product_id.name')
    uom = fields.Many2one('uom.uom', string='UOM')
    production_order_product_qty = fields.Float(digits='Product Unit of Measure')  # ghi lại giá trị production_order tại thời điểm được tạo
    production_line_product_qty = fields.Float(digits='Product Unit of Measure')  # ghi lại giá trị production_line tại thời điểm được tạo
    product_qty = fields.Float('Quantity', digits='Product Unit of Measure')
    product_plan_qty = fields.Float('Plan Quantity', digits='Product Unit of Measure', compute='_compute_product_plan_qty', inverse='_inverse_product_plan_qty', store=1)
    product_remain_qty = fields.Float('Remain Quantity', digits='Product Unit of Measure', compute='_compute_product_remain_qty', store=1)
    is_from_po = fields.Boolean(default=False)
    type_cost_product = fields.Selection(related='product_id.product_tmpl_id.x_type_cost_product')
    production_line_price_unit = fields.Float(digits='Product Unit of Measure')
    price_unit = fields.Float(string='Giá')


    @api.depends('purchase_order_line_id.product_qty', 'production_order_product_qty', 'production_line_product_qty')
    def _compute_product_plan_qty(self):
        for rec in self:
            if rec.production_line_product_qty > 0:
                rec.product_qty = rec.purchase_order_line_id.product_qty * rec.production_line_product_qty
            else:
                rec.product_qty = 0


    def _inverse_product_plan_qty(self):
        pass

