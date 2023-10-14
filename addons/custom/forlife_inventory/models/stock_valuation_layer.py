from odoo import api, fields, models
from odoo.addons.stock_account.models.stock_valuation_layer import StockValuationLayer as InheritStockValuationLayerCore
from odoo.exceptions import ValidationError

def _validate_accounting_entries(self):
    am_vals = []
    company_other_id = self.env['res.company'].sudo().search([('code', '=', '1400')])
    reason_type_5 = self.env['forlife.reason.type'].sudo().search([('code', '=', 'N02'), ('company_id', '=', company_other_id.id)])
    reason_type_4 = self.env['forlife.reason.type'].sudo().search([('code', '=', 'X02'), ('company_id', '=', company_other_id.id)])
    location_enter_inventory_balance_auto = self.env['stock.location'].sudo().search([('code', '=', 'N0701'), ('company_id', '=', company_other_id.id)])
    location_dest_check_company = self.env['stock.location'].sudo().search([('code', '=', 'X0202'), ('company_id', '=', company_other_id.id)])
    for svl in self:
        company_id = svl.company_id.id
        location_check_id = self.env['stock.location'].sudo().search([('code', '=', 'N0202'), ('company_id', '=', company_id)])
        location_dest_check_id = self.env['stock.location'].sudo().search([('code', '=', 'X0202'), ('company_id', '=', company_id)])
        reason_type_check = self.env['forlife.reason.type'].sudo().search([('code', '=', 'N05'), ('company_id', '=', company_id)])
        auto_import_check = self.env['forlife.reason.type'].sudo().search([('code','=','N0601'), ('company_id','=',company_id)])
        auto_export_check = self.env['forlife.reason.type'].sudo().search([('code','=','X1101'), ('company_id','=',company_id)])
        if not svl.with_company(svl.company_id).product_id.valuation == 'real_time':
            continue
        # if svl.currency_id.is_zero(svl.value):
        #     if location_check_id and location_dest_check_id and svl.stock_move_id.picking_id.location_id.id != location_check_id.id and \
        #             svl.stock_move_id.picking_id.location_dest_id.id != location_dest_check_id.id and \
        #             svl.stock_move_id.picking_id.reason_type_id.id != reason_type_check or (
        #             svl.stock_move_id.picking_id.location_id.id == auto_import_check or
        #             svl.stock_move_id.picking_id.location_dest_id.id == auto_export_check):
        #         continue
        company_code = svl.stock_move_id.picking_id.company_id.code
        if svl.stock_move_id.picking_id.from_po_give and company_code == '1400':
            continue
        if company_code == '1400' and svl.stock_move_id.picking_id.reason_type_id.id in [reason_type_4.id,
                                                                                         reason_type_5.id] and svl.stock_move_id.picking_id.location_id.id == location_enter_inventory_balance_auto.id \
                and svl.stock_move_id.picking_id.location_dest_id.id_deposit:
            continue
        if company_code == '1400' and svl.stock_move_id.picking_id.reason_type_id.id in [reason_type_4.id,
                                                                                         reason_type_5.id] and svl.stock_move_id.picking_id.location_dest_id.id == location_dest_check_company.id and svl.stock_move_id.picking_id.location_id.id_deposit:
            continue
        move = svl.stock_move_id
        if not move:
            move = svl.stock_valuation_layer_id.stock_move_id

        move_vals = move.with_company(svl.company_id)._account_entry_move(svl.quantity, svl.description, svl.id, svl.value)

        # Update sổ nhật ký khi tạo bút toán Chênh lệch giá trị Nhập kho và Lên hóa đơn
        if svl.price_diff_value and svl.account_move_id.move_type == 'in_invoice' and move_vals:
            domain = [('type', '=', 'general'), ('company_id', '=', company_id)]
            if svl.price_diff_value > 0:
                domain.append(('code', '=', 'GL02'))
            else:
                domain.append(('code', '=', 'GL01'))
            journal_id = self.env['account.journal'].search(domain, limit=1)
            if not journal_id:
                raise ValidationError("Các bút toán 'Chênh lệch giá trị nhập kho và lên hóa đơn' đang hạch toán vào sổ nhật ký có mã 'GL01' và 'GL02'. Hiện tại không thấy trong hệ thống, vui lòng cấu hình thêm trong phân hệ Kế toán!")
            move_vals[0]['journal_id'] = journal_id.id
        am_vals += move_vals
    if am_vals:
        account_moves = self.env['account.move'].sudo().create(am_vals)
        account_moves._post()
    for svl in self:
        # Eventually reconcile together the invoice and valuation accounting entries on the stock interim accounts
        if svl.company_id.anglo_saxon_accounting:
            svl.stock_move_id._get_related_invoices()._stock_account_anglo_saxon_reconcile_valuation(product=svl.product_id)


InheritStockValuationLayerCore._validate_accounting_entries = _validate_accounting_entries
