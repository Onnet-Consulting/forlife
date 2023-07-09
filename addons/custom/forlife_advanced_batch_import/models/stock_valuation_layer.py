from odoo import fields, models, api
from datetime import datetime

class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    def _validate_accounting_entries(self):
        context = self.env.context
        if not context.get('run_job', False):
            if self.stock_move_id.picking_type_id.warehouse_id:
                model_job_channel = self.env['queue.job.channel'].sudo()
                job_name = 'wh_'+self.stock_move_id.picking_type_id.warehouse_id.code+'_job_channel'
                job_channel = model_job_channel.search([('name', '=', job_name)], limit=1)
                channel_root = self.env.ref('queue_job.channel_root')
                if not job_channel:
                    model_job_channel.create({
                        'name': job_name,
                        'parent_id': channel_root.id
                    })
                return super(StockValuationLayer, self).with_context(run_job=True).with_delay(channel=job_name)._validate_accounting_entries()
            return super(StockValuationLayer, self).with_context(run_job=True).with_delay(channel='validate_stock_valuation_2')._validate_accounting_entries()
        return super(StockValuationLayer, self)._validate_accounting_entries()
    #     am_vals = []
    #     for svl in self:
    #         if not svl.with_company(svl.company_id).product_id.valuation == 'real_time':
    #             continue
    #         if svl.currency_id.is_zero(svl.value):
    #             continue
    #         move = svl.stock_move_id
    #         if not move:
    #             move = svl.stock_valuation_layer_id.stock_move_id
    #         am_vals += move.with_company(svl.company_id)._account_entry_move(svl.quantity, svl.description, svl.id,
    #                                                                          svl.value)
    #     self.with_delay(channel='validate_stock_valuation_2', priority=1, eta=0)._create_and_post_account_move(am_vals)
    #
    # def _create_and_post_account_move(self, am_vals):
    #     if am_vals:
    #         account_moves = self.env['account.move'].sudo().create(am_vals)
    #         account_moves._post()
    #     for svl in self:
    #         # Eventually reconcile together the invoice and valuation accounting entries on the stock interim accounts
    #         if svl.company_id.anglo_saxon_accounting:
    #             svl.stock_move_id._get_related_invoices()._stock_account_anglo_saxon_reconcile_valuation(
    #                 product=svl.product_id)