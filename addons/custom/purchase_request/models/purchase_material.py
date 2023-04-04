import json

from odoo import api, fields, models, _


class PurchaseMaterial(models.Model):
    _name = 'purchase.material'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _rec_name = 'source_document'
    _description = 'Purchase Material'

    source_document = fields.Char()
    location_from = fields.Many2one('stock.warehouse')
    location_to = fields.Many2one('stock.warehouse')
    purchase_material_line_ids = fields.One2many('purchase.material.line', 'purchase_material_id')
    status = fields.Selection([
        ('draft', 'Draft'),
        ('approve', 'Approve'),
        ('cancel', 'Cancel'),
    ], default='draft')

    def action_approve(self):
        self.write({
            'status': 'approve'
        })

    def action_cancel(self):
        self.write({
            'status': 'cancel'
        })

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Download Template for Materials'),
            'template': '/purchase_request/static/src/xlsx/template_materials.xlsx?download=true'
        }]


class PurchaseMaterialLine(models.Model):
    _name = 'purchase.material.line'
    _description = 'Purchase Material Line'

    def _default_product_domain(self):
        return [('id', '=', 0)]

    purchase_material_id = fields.Many2one('purchase.material', ondelete='cascade')
    purchase_order_line_id = fields.Many2one('purchase.order.line', ondelete='cascade')
    product_id = fields.Many2one('product.product')
    description = fields.Char(related='product_id.name')
    free_good = fields.Boolean(string='Free Goods')
    purchase_quantity = fields.Float('Purchase Quantity', digits='Product Unit of Measure')
    purchase_uom = fields.Many2one('uom.uom', string='Purchase UOM')
    exchange_quantity = fields.Float('Exchange Quantity')
    product_qty = fields.Float('Quantity', digits='Product Unit of Measure')
    purchase_material_line_item_ids = fields.One2many('purchase.material.line.item', 'purchase_material_line_id')
    product_domain = fields.Char(default=_default_product_domain)

    @api.onchange('product_domain')
    def _onchange_product_domain(self):
        production_order = self.env['production.order'].search([('type', '=', 'normal')])
        if production_order:
            product_domain = [('id', 'in', production_order.mapped('product_id.id'))]
        else:
            product_domain = self.product_domain
        return {
            'domain': {'product_id': product_domain}
        }

    @api.onchange('product_id')
    def _onchange_product_id(self):
        production_order = self.env['production.order'].search([('product_id', '=', self.product_id.id), ('type', '=', 'normal')], limit=1)
        data = []
        for line in production_order.order_line_ids:
            data.append((0, 0, {
                'product_id': line.product_id,
            }))
        self.purchase_material_line_item_ids = [(5, 0, 0)] + data

    def action_open_formview(self):
        self.ensure_one()
        view_id = self.env.ref('purchase_request.purchase_material_line_form').id
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


class PurchaseMaterialLineItem(models.Model):
    _name = 'purchase.material.line.item'
    _description = 'Purchase Material Line Item'

    purchase_material_line_id = fields.Many2one('purchase.material.line', ondelete='cascade')
    product_id = fields.Many2one('product.product')
    description = fields.Char(related='product_id.name')
    product_qty = fields.Float('Quantity', digits='Product Unit of Measure')
    price_cost = fields.Float()
    uom = fields.Many2one('uom.uom', string='UOM')
