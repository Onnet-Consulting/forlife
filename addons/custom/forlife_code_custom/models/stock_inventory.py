from odoo import api, fields, models, _


class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    @api.model_create_multi
    def create(self, vals):
        result = super(StockInventory, self).create(vals)
        for res in result:
            location_code = res.location_id.code or ''
            location_des_code = res.location_id.code or ''
            declare_code_id = self.env['declare.code']._get_declare_code('024', self.env.company.id)
            if declare_code_id:
                res.name = declare_code_id.genarate_code('stock_inventory','name',location_code,location_des_code)
        return result

