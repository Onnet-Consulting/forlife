from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    other_picking_type_id = fields.Many2one('stock.picking.type', string="Kiểu giao nhận xuất/nhập khác")
    other_location_id = fields.Many2one('stock.location', string="Lý do xuất/nhập khác mặc định")

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    return_reason = fields.Selection([
        ('invalid', 'Nhập sai'),
        ('faulty', 'Trả hàng do lỗi'),
        ('diff', 'Trả hàng do chênh lệch')
    ], string='Lí do trả hàng')

    def _action_done(self):
        if not self._context.get('endloop'):
            for picking in self:
                if not picking.purchase_id.is_inter_company and picking.x_is_check_return:
                    purchase_origin_id = picking.purchase_id if picking.purchase_id else picking.move_ids.purchase_line_id.origin_po_line_id.order_id
                    order_line = purchase_origin_id.order_line.filtered(lambda x: x.product_id.id in picking.move_ids.product_id.ids)
                    material_line = order_line.purchase_order_line_material_line_ids.filtered(lambda x: not x.type_cost_product)
                    if material_line:
                        picking.create_return_valuation_npl()
                        picking.create_return_valuation_entries()
                    if purchase_origin_id:
                        picking.tax_return_by_return_goods()
        res = super(StockPicking, self)._action_done()
        # if res and self:
        #     purchase = self.env['purchase.order']
        #     if any(self.move_ids.filtered(lambda x: x.origin_returned_move_id and x.purchase_line_id)):
        #         purchase = self.move_ids.purchase_line_id.order_id
        #     if purchase:
        #         purchase.auto_return_with_inter_company()

        return res

    def tax_return_by_return_goods(self):
        if self.move_ids.sale_line_id or self.move_ids.origin_returned_move_id.sale_line_id:
            return
        po = self.move_ids.origin_returned_move_id.purchase_line_id.order_id or self.move_ids.purchase_line_id.order_id
        if not po:
            return
        if self.move_ids.origin_returned_move_id:
            self.revert_tax_by_return_goods(po, 'inv')
        else:
            self.revert_tax_by_return_goods(po)

    def revert_tax_by_return_goods(self, po, type=None):
        move_values = []
        for line in po.purchase_synthetic_ids:
            if line.tax_amount > 0:
                amount = line.tax_amount
                product_tax = self.env.ref('forlife_purchase.product_import_tax_default')
                move_values.extend(self.prepare_move_values(line=line, amount=amount, product_tax=product_tax))
            if line.special_consumption_tax_amount > 0:
                amount = line.special_consumption_tax_amount
                product_tax = self.env.ref('forlife_purchase.product_excise_tax_default')
                move_values.extend(self.prepare_move_values(line=line, amount=amount, product_tax=product_tax))
        if type and type == 'inv':
            cost_move_values = self.prepare_move_value_with_cost(po)
            move_values += cost_move_values

        moves = self.env['account.move'].create(move_values)
        if moves:
            moves._post()

    def prepare_move_values(self, line, amount, product_tax):
        qty_po_origin = line.product_qty
        move_values = []
        journal_id = self.env['account.journal'].search([('code', '=', 'EX02'), ('type', '=', 'general')], limit=1).id
        if not journal_id:
            raise ValidationError("Không tìm thấy sổ nhật ký có mã 'EX02'. Vui lòng cấu hình thêm!")
        moves = self.move_ids.filtered(lambda x: x.purchase_line_id.id == line.id)
        for move in moves:
            qty_po_done = sum(move.mapped('quantity_done'))
            po = line.order_id
            move_value = {
                'ref': f"{self.name}",
                'purchase_type': po.purchase_type,
                'move_type': 'entry',
                'reference': po.name,
                'stock_move_id': move.id,
                'journal_id': journal_id,
                'exchange_rate': po.exchange_rate,
                'date': datetime.now(),
                'invoice_payment_term_id': po.payment_term_id.id,
                'invoice_date_due': po.date_planned,
                'restrict_mode_hash_table': False,
            }
            svl_values = []
            move_lines = [(0, 0, {
                'sequence': 1,
                'account_id': product_tax.categ_id.property_stock_account_input_categ_id.id,
                'product_id': move.product_id.id,
                'name': product_tax.name,
                'text_check_cp_normal': line.product_id.name,
                'credit': 0,
                'debit': (amount / qty_po_origin) * qty_po_done
            })]
            if move.product_id.type in ('product', 'consu'):
                svl_values.append((0, 0, {
                    'value': -abs((amount / qty_po_origin) * qty_po_done),
                    'unit_cost': amount / qty_po_origin,
                    'quantity': 0,
                    'remaining_qty': 0,
                    'description': f"{self.name} - {line.product_id.name}",
                    'product_id': move.product_id.id,
                    'company_id': self.env.company.id,
                    'stock_move_id': move.id
                }))
                if move.product_id.cost_method == 'average':
                        self.add_cost_product(move.product_id, -abs((amount / qty_po_origin) * qty_po_done))
                move_lines += [(0, 0, {
                    'sequence': 2,
                    'account_id': move.product_id.categ_id.property_stock_valuation_account_id.id,
                    'product_id': move.product_id.id,
                    'name': product_tax.name,
                    'text_check_cp_normal': line.product_id.name,
                    'credit': (amount / qty_po_origin) * qty_po_done,
                    'debit': 0,
                })]

            move_value.update({
                'stock_valuation_layer_ids': svl_values,
                'line_ids': move_lines
            })
            move_values.append(move_value)
        return move_values

    def prepare_move_value_with_cost(self, po):
        self.ensure_one()
        entries_values = []
        journal_id = self.env['account.journal'].search([('code', '=', 'EX02'), ('type', '=', 'general')], limit=1).id
        if not journal_id:
            raise ValidationError("Không tìm thấy sổ nhật ký có mã 'EX02'. Vui lòng cấu hình thêm!")
        for move in self.move_ids:
            if move.product_id.type not in ('product', 'consu'):
                continue
            product_po = po.order_line.filtered(lambda x: x.product_id == move.product_id)
            po_total_qty = sum(product_po.mapped('product_qty'))
            amount_rate = sum(product_po.mapped('total_vnd_amount')) / sum(po.order_line.mapped('total_vnd_amount'))
            for expense in po.cost_line:
                expense_vnd_amount = round(expense.vnd_amount * amount_rate, 0)
                sp_total_qty = - move.quantity_done
                unit_cost = expense_vnd_amount / po_total_qty

                if sp_total_qty == 0:
                    continue

                if not expense.product_id.categ_id.property_stock_account_input_categ_id:
                    raise ValidationError("Bạn chưa cấu hình tài khoản nhập kho trong danh mục nhóm sản phẩm của sản phẩm %s" % expense.product_id.display_name)

                entries_values += [{
                    'ref': f"{self.name}",
                    'purchase_type': po.purchase_type,
                    'move_type': 'entry',
                    'journal_id': journal_id,
                    'x_entry_types': 'entry_cost',
                    'reference': po.name,
                    'exchange_rate': po.exchange_rate,
                    'date': datetime.utcnow(),
                    'invoice_payment_term_id': po.payment_term_id.id,
                    'invoice_date_due': po.date_planned,
                    'restrict_mode_hash_table': False,
                    'stock_move_id': move.id,
                    'stock_valuation_layer_ids': [(0, 0, {
                        'value': round(unit_cost * sp_total_qty),
                        'unit_cost': unit_cost,
                        'quantity': 0,
                        'remaining_qty': 0,
                        'description': f"{self.name} - {expense.product_id.name}",
                        'product_id': move.product_id.id,
                        'company_id': self.env.company.id,
                        'stock_move_id': move.id
                    })],
                    'invoice_line_ids': [(0, 0, {
                        'sequence': 1,
                        'account_id': expense.product_id.categ_id.property_stock_account_input_categ_id.id,
                        'product_id': move.product_id.id,
                        'name': expense.product_id.name,
                        'text_check_cp_normal': expense.product_id.name,
                        'debit': abs(round(unit_cost * sp_total_qty)),
                        'credit': 0
                    }),
                    (0, 0, {
                         'sequence': 2,
                         'account_id': move.product_id.categ_id.property_stock_valuation_account_id.id,
                         'product_id': move.product_id.id,
                         'name': move.product_id.name,
                         'text_check_cp_normal': move.product_id.name,
                         'debit': 0,
                         'credit': abs(round(unit_cost * sp_total_qty))
                    })],
                }]
                for value in entries_values:
                    credit = 0.0
                    for line in value['invoice_line_ids'][1:]:
                        if credit:
                            line[-1]['credit'] += round(credit)
                            credit = 0.0
                        else:
                            credit = line[-1]['credit'] - round(line[-1]['credit'])
                            line[-1]['credit'] = round(line[-1]['credit'])
                if move.product_id.cost_method == 'average':
                    self.add_cost_product(move.product_id, round(unit_cost * sp_total_qty))
        return entries_values

    def _get_picking_info_return(self, po):
        picking_type_id =  False
        if po and po.location_export_material_id:
            picking_type_id = po.location_export_material_id.warehouse_id.in_type_id
        if not picking_type_id:
            picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'incoming'), ('company_id', '=', self.env.company.id)], limit=1)

        location_id = self.env['stock.location'].search([('code', '=', 'N0701'), ('company_id', '=', self.env.company.id)], limit=1)
        if not location_id:
            raise ValidationError("Hiện tại sản phẩm xuất trả có sản phẩm đính kèm NPL. Nhưng trong cấu hình Lý Do Nhập Khác chưa định nghĩa loại lý do có mã: N0701. Yêu cầu liên hệ admin để xử lý")
        if not location_id.reason_type_id:
            raise ValidationError("Bạn chưa có loại lý do Nhập trả nguyên phụ liệu \n Gợi ý: Cấu hình trong lý do Nhập Khác có mã: N0701")

        return picking_type_id, location_id

    def create_return_picking_npl(self, po, record, lines_npl):
        picking_type_id, location_id = self._get_picking_info_return(po)

        vals = {
            "is_locked": True,
            "immediate_transfer": False,
            'reason_type_id': location_id.reason_type_id.id,
            'location_id': location_id.id,
            'location_dest_id': po.location_export_material_id.id,
            'scheduled_date': fields.datetime.now(),
            'origin': po.name if po else record.name,
            'state': 'assigned',
            'picking_type_id': picking_type_id.id,
            'move_ids_without_package': lines_npl,
            'other_import': True
        }
        picking_npl = self.env['stock.picking'].with_context({'skip_immediate': True, 'endloop': True}).create(vals)
        ctx = picking_npl._context.copy()
        ctx.update({'extend_account_npl': True})
        picking_npl.with_context(ctx).button_validate()
        record.write({'picking_xk_id': picking_npl.id})
        return picking_npl

    def create_return_valuation_npl(self):
        lines_npl = []
        picking_type_id, npl_location_id = self._get_picking_info_return(self.purchase_id)
        if not self.purchase_id.is_return:
            for move in self.move_ids:
                for material_line_id in move.purchase_line_id.purchase_order_line_material_line_ids.filtered(lambda x: not x.type_cost_product):
                    data = self._prepare_material_lines(move, material_line_id, npl_location_id, move.purchase_line_id)
                    lines_npl.append(data)
        else:
            for move in self.move_ids:
                purchase_line_id = move.purchase_line_id.origin_po_line_id if move.purchase_line_id.origin_po_line_id else move.purchase_line_id
                for material_line_id in purchase_line_id.purchase_order_line_material_line_ids.filtered(lambda x: not x.type_cost_product):
                    data = self._prepare_material_lines(move, material_line_id, npl_location_id, purchase_line_id)
                    lines_npl.append(data)

        if lines_npl:
            self.create_return_picking_npl(self.purchase_id, self, lines_npl)
        return True

    def _prepare_material_lines(self, move, material_line_id, npl_location_id, purchase_line_id):
        product_plan_qty = move.quantity_done * (material_line_id.product_qty / purchase_line_id.product_qty)
        return (0, 0, {
            'product_id': material_line_id.product_id.id,
            'product_uom': material_line_id.uom.id or material_line_id.product_id.uom_id.id,
            'price_unit': material_line_id.production_line_price_unit,
            'location_id': npl_location_id.id,
            'location_dest_id': self.location_id.id,
            'product_uom_qty': product_plan_qty,
            'quantity_done': product_plan_qty,
            'amount_total': material_line_id.production_line_price_unit * product_plan_qty,
            'reason_type_id': npl_location_id.reason_type_id.id or False,
            'reason_id': npl_location_id.id,
            'purchase_line_id': material_line_id.purchase_order_line_id.id,
            'include_move_id': move.id
        })
    
    def create_return_valuation_entries(self):
        journal_id = self.env['account.journal'].search([('code', '=', 'EX02'), ('type', '=', 'general')], limit=1).id
        if not journal_id:
            raise ValidationError("Không tìm thấy sổ nhật ký có mã 'EX02'. Vui lòng cấu hình thêm!")
        po = self.purchase_id
        if not po:
            return
        ### Tìm kho xuất
        picking_type_id, export_production_order = self._get_picking_info_return(po)
        if not export_production_order.x_property_valuation_out_account_id:
            raise ValidationError('Bạn chưa có hoặc chưa cấu hình tài khoản trong lý do nhập nguyên phụ liệu \n Gợi ý: Tạo lý do trong cấu hình Lý do nhập khác và xuất khác có mã: N0701')
        else:
            if not export_production_order.reason_type_id:
                raise ValidationError('Bạn chưa cấu hình loại lý do cho lý do nhập khác có mã: N0701')
        account_export_production_order = export_production_order.x_property_valuation_out_account_id
        for move in self.move_ids:
            invoice_line_ids = []
            list_allowcation_npls = []
            qty_po_done = sum(move.mapped('quantity_done'))
            item = move.purchase_line_id
            material = self.env['purchase.order.line.material.line'].search([('purchase_order_line_id', '=', item.id)])

            if item.product_id.categ_id and item.product_id.categ_id.with_company(self.company_id).property_stock_valuation_account_id:
                account_1561 = item.product_id.categ_id.with_company(self.company_id).property_stock_valuation_account_id.id
            else:
                raise ValidationError(_("Bạn chưa cấu hình tài khoản định giá tồn kho trong danh mục sản phẩm của sản phẩm có tên %s") % item.product_id.name)

            credit_cost = 0
            total_npl_amount = 0
            for material_line in material:
                if material_line.product_id.product_tmpl_id.x_type_cost_product in ('labor_costs', 'internal_costs'):
                    if not material_line.product_id.categ_id or not material_line.product_id.categ_id.with_company(self.company_id).property_stock_account_input_categ_id:
                        raise ValidationError(_("Bạn chưa cấu hình tài khoản nhập kho trong danh mực sản phẩm của %s") % material_line.product_id.name)
                    if material_line.price_unit > 0:
                        pbo = material_line.price_unit * move.quantity_done * material_line.production_line_product_qty / material_line.production_order_product_qty
                        debit_cp = (0, 0, {
                            'sequence': 99991,
                            'account_id': material_line.product_id.categ_id.with_company(self.company_id).property_stock_account_input_categ_id.id,
                            'product_id': move.product_id.id,
                            'name': material_line.product_id.name,
                            'text_check_cp_normal': move.product_id.name,
                            'debit': pbo,
                            'credit': 0,
                        })
                        invoice_line_ids.append(debit_cp)
                        credit_cost += pbo
                else:
                    #tạo bút toán npl ở bên bút toán sinh với khi nhập kho khác với phiếu xuất npl
                    if item.product_id.id == material_line.purchase_order_line_id.product_id.id:
                        if material_line.product_id.standard_price > 0:
                            value = ((move.quantity_done / item.product_qty * material_line.product_qty) * material_line.product_id.standard_price)
                            #xử lý phân bổ nguyên vật liệu
                            debit_allowcation_npl = (0, 0, {
                                'sequence': 1,
                                'product_id': material_line.product_id.id,
                                'account_id': account_export_production_order.id, #tiennq
                                'name': account_export_production_order.name,
                                'debit': value,
                                'credit': 0,
                            })
                            list_allowcation_npls.append(debit_allowcation_npl)
                            credit_allowcation_npl = (0, 0, {
                                'sequence': 2,
                                'product_id': move.product_id.id,
                                'account_id': account_1561,
                                'name': move.product_id.name,
                                'debit': 0,
                                'credit': value,
                            })
                            list_allowcation_npls.append(credit_allowcation_npl)
                            total_npl_amount += value
            if credit_cost > 0:
                credit_cp = (0, 0, {
                    'sequence': 9,
                    'account_id': account_1561,
                    'product_id': move.product_id.id,
                    'name': item.product_id.name,
                    'text_check_cp_normal': item.product_id.name,
                    'debit': 0,
                    'credit': credit_cost,
                })
                invoice_line_ids.append(credit_cp)

                svl_values = [(0, 0, {
                    'value': - credit_cost,
                    'unit_cost': credit_cost / qty_po_done,
                    'quantity': 0,
                    'remaining_qty': 0,
                    'description': f"{self.name} - {item.product_id.name}",
                    'product_id': move.product_id.id,
                    'company_id': move.company_id.id,
                    'stock_move_id': move.id
                })]
                if move.product_id.cost_method == 'average':
                    self.add_cost_product(move.product_id, -credit_cost)
                entry_cp = self.env['account.move'].create({
                    'ref': f"{self.name}",
                    'purchase_type': po.purchase_type,
                    'move_type': 'entry',
                    'journal_id': journal_id,
                    'x_entry_types': 'entry_cost_labor',
                    'reference': po.name,
                    'exchange_rate': po.exchange_rate,
                    'date': datetime.now(),
                    'invoice_payment_term_id': po.payment_term_id.id,
                    'invoice_date_due': po.date_planned,
                    'stock_move_id': move.id,
                    'invoice_line_ids': invoice_line_ids,
                    'restrict_mode_hash_table': False,
                    'stock_valuation_layer_ids': svl_values
                })
                entry_cp._post()

            if list_allowcation_npls:
                svl_allowcation_values = [(0, 0, {
                    'value': -total_npl_amount,
                    'unit_cost': total_npl_amount / qty_po_done,
                    'quantity': 0,
                    'remaining_qty': 0,
                    'description': f"{self.name} - {item.product_id.name}",
                    'product_id': move.product_id.id,
                    'company_id': move.company_id.id,
                    'stock_move_id': move.id
                })]
                if move.product_id.cost_method == 'average':
                    self.add_cost_product(move.product_id, -total_npl_amount)
                entry_allowcation_npls = self.env['account.move'].create({
                    'ref': f"{self.name} - Phân bổ nguyên phụ liệu",
                    'purchase_type': po.purchase_type,
                    'move_type': 'entry',
                    'journal_id': journal_id,
                    # 'x_entry_types': 'entry_material',
                    'reference': po.name,
                    'exchange_rate': po.exchange_rate,
                    'date': datetime.now(),
                    'invoice_payment_term_id': po.payment_term_id.id,
                    'invoice_date_due': po.date_planned,
                    'invoice_line_ids': list_allowcation_npls,
                    'restrict_mode_hash_table': False,
                    'stock_move_id': move.id,
                    'stock_valuation_layer_ids': svl_allowcation_values
                })
                entry_allowcation_npls._post()
