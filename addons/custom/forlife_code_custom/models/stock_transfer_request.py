from odoo import api, fields, models, _


class StockTransferRequest(models.Model):
    _inherit = 'stock.transfer.request'

    @api.model_create_multi
    def create(self, vals):
        result = super(StockTransferRequest, self).create(vals)
        sequence = 0
        for res in result:
            declare_code_id = self.env['declare.code']._get_declare_code('018', self.env.company.id)
            if declare_code_id:
                res.name = declare_code_id.genarate_code('stock_transfer_request','name',sequence)
                sequence += 1
        return result

