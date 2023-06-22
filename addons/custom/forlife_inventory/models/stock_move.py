from odoo import api, fields, models
from odoo.exceptions import ValidationError

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _account_entry_move(self, qty, description, svl_id, cost):
        am_vals = super(StockMove, self)._account_entry_move(qty, description, svl_id, cost)
        journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation()
        if self._is_give():
            am_vals.append(self.with_context(_is_give=True).with_company(self.mapped('move_line_ids.location_id.company_id'))._prepare_account_move_vals(acc_src, acc_valuation, journal_id, qty, description, svl_id, cost))
        return am_vals

    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description):
        # This method returns a dictionary to provide an easy extension hook to modify the valuation lines (see purchase for an example)
        self.ensure_one()
        s_location_pos = self.env.ref('forlife_stock.warehouse_for_pos', raise_if_not_found=False).id
        s_location_sell_ecommerce = self.env.ref('forlife_stock.sell_ecommerce', raise_if_not_found=False).id
        warehouse_type_master = self.env.ref('forlife_base.stock_warehouse_type_01', raise_if_not_found=False).id
        rslt = super(StockMove, self)._generate_valuation_lines_data(partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description)
        if '_is_give' in self._context and self._context.get('_is_give'):
            if self.location_id.warehouse_id.whs_type.id in [warehouse_type_master] and self.location_dest_id.stock_location_type_id.id in [s_location_pos] and self.location_dest_id.id_deposit:
                rslt['credit_line_vals']['account_id'] = self.location_dest_id.account_stock_give.id
            if self.location_id.stock_location_type_id.id in [s_location_pos] and self.location_dest_id.warehouse_id.whs_type.id in [warehouse_type_master] and self.location_id.id_deposit:
                rslt['credit_line_vals']['account_id'] = self.product_id.categ_id.property_stock_valuation_account_id.id
                rslt['debit_line_vals']['account_id'] = self.location_id.account_stock_give.id
            if self.location_id.stock_location_type_id.id in [s_location_sell_ecommerce, s_location_pos] and self.location_dest_id.stock_location_type_id.id in [s_location_pos, s_location_sell_ecommerce]:
                if self.location_id.id_deposit and self.location_id.account_stock_give:
                    account_stock_give_id = self.location_id.account_stock_give.id
                    if not account_stock_give_id:
                        raise ValidationError('Chưa cấu hình tài khoản kí gửi!')
                    else:
                        rslt['credit_line_vals']['account_id'] = account_stock_give_id
                if self.location_dest_id.id_deposit and self.location_dest_id.id_deposit:
                    account_stock_give_id = self.location_dest_id.account_stock_give.id
                    if not account_stock_give_id:
                        raise ValidationError('Chưa cấu hình tài khoản kí gửi!')
                    else:
                        rslt['credit_line_vals']['account_id'] = account_stock_give_id
        return rslt

    @api.model
    def _get_valued_types(self):
        rslt = super(StockMove, self)._get_valued_types()
        """add new location type
        """
        rslt.append('give')
        return rslt

    def _is_give(self):
        """Check if the move should be considered as entering the company so that the cost method
        will be able to apply the correct logic.

        :returns: True if the move is entering the company else False
        :rtype: bool
        """
        self.ensure_one()
        if self._get_give_move_lines() and not self._is_dropshipped_returned():
            return True
        return False

    def _get_give_move_lines(self):
        res = self.env['stock.move.line']
        for move_line in self.move_line_ids:
            if move_line.owner_id and move_line.owner_id != move_line.company_id.partner_id:
                continue
            if move_line.picking_id.from_company and move_line.picking_id.from_company.code == '1300' and move_line.picking_id.to_company and move_line.picking_id.to_company.code == '1400':
                res |= move_line
        return res

    def _create_give_svl(self, forced_quantity=None):
        """Create a `stock.valuation.layer` from `self`.

        :param forced_quantity: under some circunstances, the quantity to value is different than
            the initial demand of the move (Default value = None)
        """
        svl_vals_list = []
        for move in self:
            move = move.with_company(move.company_id)
            valued_move_lines = move._get_give_move_lines()
            valued_quantity = 0
            for valued_move_line in valued_move_lines:
                valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)
            if float_is_zero(forced_quantity or valued_quantity, precision_rounding=move.product_id.uom_id.rounding):
                continue
            svl_vals = move.product_id._prepare_out_svl_vals(forced_quantity or valued_quantity, move.company_id)
            svl_vals.update(move._prepare_common_svl_vals())
            svl_vals['description'] += svl_vals.pop('rounding_adjustment', '')
            svl_vals_list.append(svl_vals)
        res = self.env['stock.valuation.layer'].sudo().create(svl_vals_list)
        return res