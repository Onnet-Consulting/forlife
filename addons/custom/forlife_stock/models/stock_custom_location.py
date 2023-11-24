from odoo import fields, models, api, _
from odoo.exceptions import AccessError, ValidationError
import logging
_logger = logging.getLogger(__name__)


class Location(models.Model):
    _inherit = 'stock.location'

    code = fields.Char(string='Mã', required=True)
    type_other = fields.Selection([('incoming', 'Nhập khác'), ('outcoming', 'Xuất khác')], string='Loại khác',
                                  required=True)
    valuation_out_account = fields.Many2one("account.account", string="Tài khoản định giá tồn kho (xuất hàng)")
    valuation_in_account = fields.Many2one("account.account", string="Tài khoản định giá tồn kho (nhập hàng)")
    id_deposit = fields.Boolean(string='Kho hàng ký gửi?', default=False)
    reason_type_id = fields.Many2one('forlife.reason.type')
    # work_order = fields.Many2one('forlife.production', string='Work Order')
    valuation_in_account_id = fields.Many2one(
        'account.account', 'Stock Valuation Account (Incoming)',
        domain=[],
        help="Used for real-time inventory valuation. When set on a virtual location (non internal type), "
             "this account will be used to hold the value of products being moved from an internal location "
             "into this location, instead of the generic Stock Output Account set on the product. "
             "This has no effect for internal locations.")
    valuation_out_account_id = fields.Many2one(
        'account.account', 'Stock Valuation Account (Outgoing)',
        domain=[],
        help="Used for real-time inventory valuation. When set on a virtual location (non internal type), "
             "this account will be used to hold the value of products being moved out of this location "
             "and into an internal location, instead of the generic Stock Output Account set on the product. "
             "This has no effect for internal locations.")

    x_property_valuation_in_account_id = fields.Many2one(
        'account.account', 'Stock Valuation Account (Incoming)',
        domain=[], company_dependent=True,
        help="Used for real-time inventory valuation. When set on a virtual location (non internal type), "
             "this account will be used to hold the value of products being moved from an internal location "
             "into this location, instead of the generic Stock Output Account set on the product. "
             "This has no effect for internal locations.")

    x_property_valuation_out_account_id = fields.Many2one(
        'account.account', 'Stock Valuation Account (Outgoing)',
        domain=[], company_dependent=True,
        help="Used for real-time inventory valuation. When set on a virtual location (non internal type), "
             "this account will be used to hold the value of products being moved out of this location "
             "and into an internal location, instead of the generic Stock Output Account set on the product. "
             "This has no effect for internal locations.")

    stock_custom_picking_id = fields.Many2one('stock.picking')

    is_price_unit = fields.Boolean(default=False)
    is_work_order = fields.Boolean(default=False)
    is_assets = fields.Boolean('Bắt buộc chọn thẻ tài sản')
    reason_export_material_id = fields.Many2one('stock.location', string='Lý do xuất NVL tương ứng', check_company=True,)

    @api.constrains('code')
    def contrainst_code(self):
        for rec in self:
            if rec.code:
                check_code_if_exist = self.env['stock.location'].search(
                    [('code', '=', rec.code), ('company_id', '=', rec.company_id.id)], limit=2)
                if len(check_code_if_exist) > 1:
                    raise ValidationError(_('Mã địa điểm phải là duy nhất trong công ty này!'))

    @api.onchange('type_other')
    def _onchange_type_other(self):
        for r in self:
            if r.type_other == 'incoming':
                r.usage = 'supplier'
            elif r.type_other == 'outcoming':
                r.usage = 'import/export'


class StockMove(models.Model):
    """Stock Valuation Layer"""

    _inherit = 'stock.move'

    # Hàm xử lý sinh bút toán nếu là nhâp khác xuất khác
    def _prepare_account_move_line(self, qty, cost, credit_account_id, debit_account_id, svl_id, description):
        """
        Generate the account.move.line values to post to track the stock valuation difference due to the
        processing of the given quant.
        """
        self.ensure_one()

        # the standard_price of the product may be in another decimal precision, or not compatible with the coinage of
        # the company currency... so we need to use round() before creating the accounting entries.

        #todo remove because cost is original not foreign currency
        '''
        if self.purchase_line_id and self.purchase_line_id.order_id.type_po_cost == 'tax' \
                and self.purchase_line_id.order_id.currency_id != self.env.company.currency_id:
            cost = cost * self.purchase_line_id.order_id.exchange_rate
        '''
        debit_value = self.company_id.currency_id.round(cost)
        credit_value = debit_value
        valuation_partner_id = self._get_partner_id_for_valuation_lines()
        if self.picking_id.location_id.id_deposit and self.picking_id.sale_id:
            if not self.picking_id.location_id.account_stock_give:
                raise ValidationError(_(f'Vui lòng cấu hình tài khoản kho kí gửi của địa điểm {self.picking_id.location_id.name_get()[0][1]}!'))
            credit_account_id = self.picking_id.location_id.account_stock_give.id
        if self.picking_id.location_dest_id.type_other == 'outcoming':
            # xử lí tài khoản khi là kiểm kê kho location kí gửi
            if self.picking_id.location_id.id_deposit and self.picking_id.location_id.account_stock_give:
                credit_account_id = self.picking_id.location_id.account_stock_give.id
                debit_account_id = self.picking_id.location_dest_id.with_company(self.picking_id.company_id).x_property_valuation_in_account_id.id
            else:
                debit_account_id = self.picking_id.location_dest_id.with_company(self.picking_id.company_id).x_property_valuation_in_account_id.id
                credit_account_id = self.product_id.categ_id.with_company(self.picking_id.company_id).property_stock_valuation_account_id.id
        if self.picking_id.location_id.type_other == 'incoming':
            # xử lí tài khoản khi là đơn đổi trả từ pos
            if self.picking_id.location_dest_id.id_deposit and self.picking_id.location_dest_id.account_stock_give:
                debit_account_id = self.picking_id.location_dest_id.account_stock_give.id
                credit_account_id = self.picking_id.location_id.x_property_valuation_out_account_id.id
                if not credit_account_id or not debit_account_id:
                    raise ValidationError (_('Vui lòng cấu hình tài khoản kho kí gửi của địa điểm này hoặc trường Stock Valuation Account (Outgoing) tại địa điểm Nhập trả lại hàng kí gửi!'))
            else:
                debit_account_id = self.product_id.categ_id.with_company(self.picking_id.company_id).property_stock_valuation_account_id.id
                credit_account_id = self.picking_id.location_id.with_company(self.picking_id.company_id).x_property_valuation_out_account_id.id
            if self.picking_id.picking_type_id.exchange_code != 'incoming' and not self.split_line_sub_id:
                if not self.picking_id.location_id.is_price_unit:
                    debit_value = credit_value = self.product_id.standard_price * self.quantity_done
                else:
                    if self.previous_qty:
                        debit_value = credit_value = (self.amount_total / self.previous_qty) * self.quantity_done
                    else:
                        debit_value = credit_value = 0
                # debit_value = credit_value = self.product_id.standard_price * self.quantity_done \
                # if not self.picking_id.location_id.is_price_unit else (self.amount_total / self.previous_qty) * self.quantity_done
            # if not self.picking_id.location_id.is_price_unit else self.price_unit * self.quantity_done
            if self.split_line_sub_id:
                debit_value = credit_value = self.split_line_sub_id.product_id.standard_price * self.quantity_done
        rslt = super(StockMove, self)._generate_valuation_lines_data(valuation_partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description)
        if self.split_line_sub_id and rslt.get('credit_line_vals'):
            rslt['credit_line_vals']['product_id'] = self.split_line_sub_id.product_id.id
        res = [(0, 0, line_vals) for line_vals in rslt.values()]
        return res

    # Hàm xử lý sửa định giá theo Price unit mới
    def _get_in_svl_vals(self, forced_quantity):
        svl_vals_list = []
        for move in self:
            move = move.with_company(move.company_id)
            valued_move_lines = move._get_in_move_lines()
            valued_quantity = 0
            for valued_move_line in valued_move_lines:
                valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)
            unit_cost = move.product_id.standard_price
            if move.product_id.cost_method != 'standard':
                unit_cost = abs(move._get_price_unit())  # May be negative (i.e. decrease an out move).
            if move.picking_id.other_import and move.picking_id.location_id.is_price_unit:
                unit_cost = move.amount_total / move.previous_qty if move.previous_qty != 0 else 0
            if move.split_line_sub_id.product_id:
                unit_cost = move.split_line_sub_id.product_id.standard_price
            svl_vals = move.product_id._prepare_in_svl_vals(forced_quantity or valued_quantity, unit_cost)
            svl_vals.update(move._prepare_common_svl_vals())
            if forced_quantity:
                svl_vals['description'] = 'Correction of %s (modification of past move)' % move.picking_id.name or move.name
            svl_vals_list.append(svl_vals)
        return svl_vals_list
