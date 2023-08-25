from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import date
import json


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    request_id = fields.Many2one('purchase.request')
    purchase_request_ids = fields.Many2many('purchase.request')
    partner_id = fields.Many2one('res.partner', required=False)
    event_id = fields.Many2one('forlife.event', string='Event Program')
    has_contract_commerce = fields.Boolean(string='Có hóa đơn hay không?')
    rejection_reason = fields.Text()
    is_check_line_material_line = fields.Boolean(compute='_compute_order_line_production_order')
    order_line_production_order = fields.One2many(comodel_name='purchase.order.line', compute='_compute_order_line_production_order')
    total_qty = fields.Float(string='Tổng số lượng', compute='compute_total_qty')

    @api.depends('order_line.purchase_quantity')
    def compute_total_qty(self):
        for rec in self:
            self._cr.execute("""
                SELECT 
                    sum(pol.purchase_quantity) as purchase_quantity
                FROM purchase_order_line pol where pol.order_id = %s;
            """ % rec.id)
            data = self._cr.dictfetchone()
            rec.total_qty = data.get('purchase_quantity', 0)

    @api.depends('order_line')
    def _compute_order_line_production_order(self):
        for order in self:
            order_line_production_order = order.order_line.filtered(lambda line: line.x_check_npl)
            order.order_line_production_order = order_line_production_order
            if not order_line_production_order or not order.order_line:
                order.is_check_line_material_line = True
            else:
                order.is_check_line_material_line = False

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
    purchase_order_line_material_line_ids = fields.One2many('purchase.order.line.material.line', 'purchase_order_line_id')
    product_type = fields.Selection(related='product_id.product_type', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', change_default=True, index='btree_not_null')
    x_check_npl = fields.Boolean(related='product_id.x_check_npl')
    material_cost = fields.Float("Chi phí NPL", compute="_compute_cost", store=1)
    labor_cost = fields.Float("Chi phí nhân công", compute="_compute_cost", store=1)

    @api.constrains('taxes_id')
    def _check_taxes_id(self):
        for line in self:
            if len(line.taxes_id) > 1:
                raise ValidationError('Only one tax can be applied to a purchase order line.')

    @api.depends('total_vnd_amount', 'before_tax', 'tax_amount', 'special_consumption_tax_amount', 'after_tax', 'material_cost', 'labor_cost')
    def _compute_total_product(self):
        super()._compute_total_product()
        for record in self:
            record.total_product += record.material_cost + record.labor_cost

    @api.depends("purchase_order_line_material_line_ids",
                 "purchase_order_line_material_line_ids.product_id",
                 "purchase_order_line_material_line_ids.product_id.standard_price",
                 "purchase_order_line_material_line_ids.product_qty",
                 "purchase_order_line_material_line_ids.price_unit")
    def _compute_cost(self):
        for item in self:
            item.material_cost = item.material_cost
            item.labor_cost = item.labor_cost

            if not item.order_id.picking_ids.picking_xk_id.filtered(lambda x: x.state == 'done'):
                total_material_price = 0
                total_labor_price = 0
                material_on_hand = item.purchase_order_line_material_line_ids.filtered(lambda x: x.product_id.detailed_type == 'product')
                labor_service = item.purchase_order_line_material_line_ids.filtered(lambda x: x.product_id.detailed_type == 'service')

                total_material_price += sum([x.product_id.standard_price * x.product_qty for x in material_on_hand])
                total_labor_price += sum([x.price_unit * x.product_qty for x in labor_service])

                item.material_cost = total_material_price
                item.labor_cost = total_labor_price

    def action_npl(self):
        self.ensure_one()
        if not self.purchase_order_line_material_line_ids:
            product = self.product_id
            production_order = self.env['production.order'].search([('product_id', '=', product.id), ('type', '=', 'normal'), ('company_id', '=', self.env.company.id)], limit=1)
            if not production_order:
                raise ValidationError('Sản phẩm không hợp lệ, vui lòng kiểm tra lại!')
            production_data = []
            for production_line in production_order.order_line_ids:
                production_data.append((0, 0, {
                    'product_id': production_line.product_id.id,
                    'uom': production_line.uom_id.id,
                    'production_order_product_qty': production_order.product_qty,
                    'production_line_product_qty': production_line.product_qty,
                    'production_line_price_unit': production_line.price,
                    'is_from_po': True,
                }))
            self.write({
                'purchase_order_line_material_line_ids': production_data
            })
        else:
            pass
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
    product_type = fields.Selection(related='product_id.detailed_type')
    production_line_product_qty = fields.Float(digits='Product Unit of Measure')  # ghi lại giá trị production_line tại thời điểm được tạo
    product_qty = fields.Float('Quantity', digits='Product Unit of Measure', compute='_compute_product_qty', store=1, readonly=False)
    is_from_po = fields.Boolean(default=False)
    type_cost_product = fields.Selection(related='product_id.product_tmpl_id.x_type_cost_product')
    production_line_price_unit = fields.Float(digits='Product Unit of Measure') # ghi lại price ở đính kèm sản phẩm ứng product
    price_unit = fields.Float(string='Giá', compute='_compute_price_unit', store=1)
    total_amount = fields.Float(string='Thành tiền', compute='_compute_total_amount', store=True)
    compute_flag = fields.Boolean(default=True)

    @api.depends('production_line_price_unit', 'product_qty')
    def _compute_price_unit(self):
        for rec in self:
            if rec.product_id.product_tmpl_id.x_type_cost_product in ('labor_costs', 'internal_costs'):
                rec.price_unit = rec.production_line_price_unit
            else:
                rec.price_unit = 0

    @api.depends('purchase_order_line_id.product_qty', 'purchase_order_line_id',
                 'compute_flag')
    def _compute_product_qty(self):
        for rec in self:
            if rec.compute_flag:
                if rec.production_line_product_qty > 0:
                    rec.product_qty = (rec.purchase_order_line_id.product_qty * rec.production_line_product_qty)/rec.production_order_product_qty
                else:
                    rec.product_qty = 0
            else:
                pass

    @api.depends('price_unit', 'product_qty')
    def _compute_total_amount(self):
        for item in self:
            item.total_amount = item.price_unit * item.product_qty

    @api.onchange('product_qty')
    def onchange_product_qty_pppp(self):
        if self.product_qty != self.purchase_order_line_id.product_qty * self.production_line_product_qty:
            self.compute_flag = False
        else:
            self.compute_flag = True
