from odoo import api, fields, models
from odoo.addons.stock_account.models.stock_valuation_layer import StockValuationLayer as InheritStockValuationLayerCore


def _validate_accounting_entries(self):
    am_vals = []
    location_check_id = self.env['stock.location'].sudo().search([('code', '=', 'N0202')], limit=1)
    location_dest_check_id = self.env['stock.location'].sudo().search([('code', '=', 'X0202')], limit=1)
    location_enter_inventory_balance_auto = self.env['stock.location'].sudo().search([('code', '=', 'X701')], limit=1)
    reason_type_check = self.env.ref('forlife_inventory.reason_type_import_return_product', raise_if_not_found=False).id
    reason_type_5 = self.env.ref('forlife_stock.reason_type_5', raise_if_not_found=False).id
    reason_type_4 = self.env.ref('forlife_stock.reason_type_4', raise_if_not_found=False).id
    auto_import_check = self.env.ref('forlife_inventory.nhap_ki_gui_tu_dong').id
    auto_export_check = self.env.ref('forlife_inventory.xuat_ki_gui_tu_dong').id
    for svl in self:
        if not svl.with_company(svl.company_id).product_id.valuation == 'real_time':
            continue
        if svl.currency_id.is_zero(svl.value):
            if location_check_id and location_dest_check_id and svl.stock_move_id.picking_id.location_id.id != location_check_id.id and \
                    svl.stock_move_id.picking_id.location_dest_id.id != location_dest_check_id.id and \
                    svl.stock_move_id.picking_id.reason_type_id.id != reason_type_check or (
                    svl.stock_move_id.picking_id.location_id.id == auto_import_check or
                    svl.stock_move_id.picking_id.location_dest_id.id == auto_export_check):
                continue
        company_code = svl.stock_move_id.picking_id.company_id.code
        if svl.stock_move_id.picking_id.from_po_give and company_code == '1400':
            continue
        if company_code == '1400' and svl.stock_move_id.picking_id.reason_type_id.id in [reason_type_4,
                                                                                    reason_type_5] and svl.stock_move_id.picking_id.location_id.id == location_enter_inventory_balance_auto.id \
                and svl.stock_move_id.picking_id.location_dest_id.id_deposit:
            continue
        if company_code == '1400' and svl.stock_move_id.picking_id.reason_type_id.id in [reason_type_4,
                                                                                    reason_type_5] and svl.stock_move_id.picking_id.location_dest_id.id == location_dest_check_id.id and svl.stock_move_id.picking_id.location_id.id_deposit:
            continue
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
