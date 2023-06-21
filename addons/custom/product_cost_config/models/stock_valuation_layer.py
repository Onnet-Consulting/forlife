from odoo import api, fields, models
from odoo.addons.stock_account.models.stock_valuation_layer import StockValuationLayer as InheritStockValuationLayerCore
from ...forlife_inventory.models.stock_valuation_layer import StockVLayer as InheritStockValuationLayerCustom


def _validate_accounting_entries(self):
        am_vals = []
        for svl in self:
            if not svl.with_company(svl.company_id).product_id.valuation == 'real_time':
                continue
            # if svl.currency_id.is_zero(svl.value):
            #     continue
            move = svl.stock_move_id
            if not move:
                move = svl.stock_valuation_layer_id.stock_move_id
            am_vals += move.with_company(svl.company_id)._account_entry_move(svl.quantity, svl.description, svl.id, svl.value)
        if am_vals:
            account_moves = self.env['account.move'].sudo().create(am_vals)
            account_moves._post()
        for svl in self:
            # Eventually reconcile together the invoice and valuation accounting entries on the stock interim accounts
            if svl.company_id.anglo_saxon_accounting:
                svl.stock_move_id._get_related_invoices()._stock_account_anglo_saxon_reconcile_valuation(product=svl.product_id)

InheritStockValuationLayerCore._validate_accounting_entries = _validate_accounting_entries
InheritStockValuationLayerCustom._validate_accounting_entries = _validate_accounting_entries
