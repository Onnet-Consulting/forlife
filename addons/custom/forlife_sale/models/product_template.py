from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_negative_value = fields.Boolean(string='Giá trị âm')
    x_free_good = fields.Boolean(string='Hàng tặng')

    @api.onchange('x_negative_value')
    def onchange_x_negative_value(self):
        if self.x_negative_value:
            self.list_price = -abs(self.list_price)
        else:
            self.list_price = abs(self.list_price)

    @api.onchange('x_free_good')
    def onchange_x_free_good(self):
        if self.x_free_good:
            self.list_price = 0
    @api.onchange('list_price')
    def onchange_list_price(self):
        self.onchange_x_free_good()
        self.onchange_x_negative_value()
