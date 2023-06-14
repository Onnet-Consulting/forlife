from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ForlifeBOM(models.Model):
    _name = 'forlife.bom'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Forlife BOM'
    _rec_name = 'forlife_production_id'

    code = fields.Char()
    name = fields.Char()

    forlife_production_id = fields.Many2one('forlife.production', required=1)
    forlife_production_name = fields.Char(related="forlife_production_id.name", required=1)
    product_id = fields.Many2one('product.product', required=1)
    description = fields.Char(string='Description', related="product_id.name", required=1)
    quantity = fields.Integer(string="Quantity", required=1)
    uom_id = fields.Many2one(related="product_id.uom_id")
    unit_prices = fields.Float(string="Unit Prices")
    prices_total = fields.Float(string="Prices Total")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('confirm', 'Confirm'),
        ('approved', 'Approved'),
        ('done', 'Done'),
    ], default='draft')
    implementation_id = fields.Many2one('account.analytic.account', string='Bộ phận thực hiện')
    management_id = fields.Many2one('account.analytic.account', string='Bộ phận quản lý')
    production_department = fields.Selection([('tu_san_xuat', 'Hàng tự sản xuất'),
                                              ('tp', 'Gia công TP'),
                                              ('npl', 'Gia công NPL')], string='Production Department')

    def update_price(self):
        current_bom = self.env['forlife.production.finished.product'].search(
            [('forlife_production_id', '=', self.forlife_production_id.id), ('product_id', '=', self.product_id.id)], limit=1)
        for record in self:
            record.write({'write_date': fields.Datetime.now(),
                          'unit_prices': sum(rec.total * rec.product_id.standard_price for rec in record.forlife_bom_material_ids) / record.quantity
                                         + sum(rec.total * rec.product_id.standard_price for rec in record.forlife_bom_ingredients_ids) / record.quantity
                                         + sum(rec.rated_level for rec in record.forlife_bom_service_cost_ids) / record.quantity})
            current_bom.write({'unit_price': record.unit_prices})

    @api.onchange('forlife_bom_material_ids', 'forlife_bom_material_ids.total')
    def _onchange_forlife_bom_material_ids(self):
        self.unit_prices = sum(rec.total * rec.product_id.standard_price for rec in self.forlife_bom_material_ids) / self.quantity if self.quantity else 0

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Tải xuống mẫu bom'),
            'template': '/forlife_purchase/static/src/xlsx/template_bom.xlsx?download=true'
        }]
