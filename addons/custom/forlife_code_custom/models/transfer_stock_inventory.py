from odoo import api, fields, models, _


class TransferStockInventory(models.Model):
    _inherit = 'transfer.stock.inventory'

    @api.model_create_multi
    def create(self, vals):
        result = super(TransferStockInventory, self).create(vals)
        sequence = 0
        for res in result:
            declare_code = '022' # Kiem ke can ton
            if res.x_classify:
                declare_code = '023'
            declare_code_id = self.env['declare.code']._get_declare_code(declare_code, res.company_id.id)
            if declare_code_id:
                res.code = declare_code_id.genarate_code(res.company_id.id,'transfer.stock.inventory','code',sequence)
                sequence += 1
        return result

