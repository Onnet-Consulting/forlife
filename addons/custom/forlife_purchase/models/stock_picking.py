from odoo import api, fields, models, _
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, format_amount, format_date, formatLang, get_lang, groupby, float_round
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
import json
from lxml import etree


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_pk_purchase = fields.Boolean(string="Là phiếu của Po", default=False)
    picking_xk_id = fields.Many2one('stock.picking', index=True, copy=False)
    account_xk_id = fields.Many2one('account.move', copy=False)

    def _check_company(self, fnames=None):
        if self._context.get('inter_company'):
            return
        return super(StockPicking, self)._check_company(fnames=fnames)

    def view_xk_picking(self):
        return {
            'name': _('Forlife Stock Exchange'),
            'view_mode': 'form',
            'res_model': self._name,
            'res_id': self.picking_xk_id.id,
            'type': 'ir.actions.act_window',
            'target': 'current'
        }

    def view_xk_account(self):
        account_ids = self.account_xk_id.ids if self.account_xk_id else []
        domain = [('id', 'in', account_ids)]
        return {
            'name': _('Forlife Account'),
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'res_id': self.picking_xk_id.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': domain
        }

    def action_cancel(self):
        for rec in self:
            if rec.picking_xk_id:
                rec.picking_xk_id.action_cancel()
                rec.picking_xk_id.action_back_to_draft()
                rec.picking_xk_id.unlink()
            if rec.account_xk_id:
                rec.account_xk_id.button_draft()
                rec.account_xk_id.button_cancel()
        return super(StockPicking, self).action_cancel()

    def action_back_to_draft(self):
        for rec in self:
            if rec.picking_xk_id:
                rec.picking_xk_id.action_cancel()
                rec.picking_xk_id.action_back_to_draft()
                rec.picking_xk_id.unlink()
            if rec.account_xk_id:
                rec.account_xk_id.button_draft()
                rec.account_xk_id.button_cancel()
                rec.account_xk_id.unlink()
        return super(StockPicking, self).action_back_to_draft()

    def check_quant_goods_import(self, po):
        self.ensure_one()
        material_line_ids = po.order_line_production_order.purchase_order_line_material_line_ids
        material_product_ids = material_line_ids.filtered(lambda x: not x.product_id.x_type_cost_product and x.product_id.detailed_type == 'product').product_id.ids
        if not material_product_ids:
            return
        if self.state == 'done':
            product_ids = [
                (quant['product_id'][0], quant['quantity'] or 0)
                for quant in self.env['stock.quant'].read_group(
                    domain=[('location_id', '=', po.location_export_material_id.id),  ('product_id', 'in', material_product_ids)],
                    fields=['quantity'],
                    groupby='product_id')
            ]
            product_not_quant = self.env['product.product'].sudo().search([
                '|', ('id', 'in', [product[0] for product in product_ids if product[1] <= 0]),
                '&', ('id', 'not in', [product[0] for product in product_ids]), ('id', 'in', material_product_ids)
            ])
            if product_not_quant:
                raise ValidationError('Những nguyên phụ liệu sau không đủ tồn kho: \n%s' % '\n'.join(product.name for product in product_not_quant))

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        if self._context.get('endloop'):
            return True
        for record in self:
            po = record.purchase_id
            if not po:
                continue
            if po.is_inter_company == False and not po.is_return and not record.move_ids[0]._is_purchase_return():
                if record.state == 'done':
                    ## check npl tồn:
                    self.check_quant_goods_import(po)
                    po.write({
                        'inventory_status': 'done',
                        'invoice_status_fake': 'to invoice',
                    })
                    _context = {
                        'pk_no_input_warehouse': False,
                    }
                    if po.type_po_cost == 'tax':
                        # tạo bút toán định giá tồn kho với thuế nhập khẩu và thuế đặc biệt
                        if po and po.exchange_rate_line_ids:
                            move_import_tax_values = self.prepare_move_svl_value_with_tax_po(po, 'import') # thuế nhập khẩu
                            move_special_tax_values = self.prepare_move_svl_value_with_tax_po(po, 'special') # thuế tiêu thụ đặc biệt
                            move_values = move_import_tax_values + move_special_tax_values
                            moves = self.env['account.move'].create(move_values)
                            if moves:
                                moves._post()
                        if po.cost_line:
                            self.create_expense_entries(po)
                            '''
                            cp = self.create_invoice_po_cost(po, record)
                            '''
                    elif po.type_po_cost == 'cost':
                        self.create_expense_entries(po)
                        '''
                        cp = self.create_invoice_po_cost(po, record)
                        '''
                    # Tạo nhập khác xuất khác khi nhập kho
                    if po.order_line_production_order and not po.is_inter_company:
                        npl = self.create_invoice_npl(po, record)
                    for rec in record.move_ids_without_package:
                        if rec.work_production:
                            quantity = self.env['quantity.production.order'].search(
                                [('product_id', '=', rec.product_id.id),
                                 ('location_id', '=', rec.picking_id.location_dest_id.id),
                                 ('production_id.code', '=', rec.work_production.code)])
                            if quantity:
                                quantity.write({
                                    'quantity': quantity.quantity + rec.quantity_done
                                })
                            else:
                                self.env['quantity.production.order'].create({
                                    'product_id': rec.product_id.id,
                                    'location_id': rec.picking_id.location_dest_id.id,
                                    'production_id': rec.work_production.id,
                                    'quantity': rec.quantity_done
                                })
                    account_move = self.env['account.move'].search([('stock_move_id', 'in', self.move_ids.ids)])
                    account_move.update({
                        'currency_id': po.currency_id.id,
                        'exchange_rate': po.exchange_rate
                    })
        return res

    def prepare_move_svl_value_with_tax_po(self, po, tax_type):
        if not po.exchange_rate_line_ids or len(po.exchange_rate_line_ids) <= 0:
            return []
        move_values = []
        for line in po.exchange_rate_line_ids:
            amount = line.tax_amount if tax_type != 'special' else line.special_consumption_tax_amount
            qty_po_origin = line.product_qty
            move = self.env['stock.move'].search([('purchase_line_id', '=', line.id), ('picking_id', '=', self.id)])
            qty_po_done = sum(move.mapped('quantity_done'))
            if tax_type != 'special':
                product_tax = self.env.ref('forlife_purchase.product_import_tax_default')
                if not product_tax.categ_id.with_company(po.company_id).property_stock_account_input_categ_id:
                    raise ValidationError("Bạn chưa cấu hình tài khoản nhập kho trong danh mục nhóm sản phẩm của sản phẩm tên là 'Thuế nhập khẩu'")
            else:
                product_tax = self.env.ref('forlife_purchase.product_excise_tax_default')
                if not product_tax.categ_id.with_company(po.company_id).property_stock_account_input_categ_id:
                    raise ValidationError("Bạn chưa cấu hình tài khoản nhập kho trong danh mục nhóm sản phẩm của sản phẩm tên là 'Thuế tiêu thụ đặc biệt'")

            move_value = {
                'ref': f"{self.name} - {line.product_id.name}",
                'purchase_type': po.purchase_type,
                'move_type': 'entry',
                'reference': po.name,
                'journal_id': self.env['account.journal'].search([('code', '=', 'EX02'), ('type', '=', 'general')], limit=1).id,
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
                'product_id': line.product_id.id,
                'name': product_tax.name,
                'text_check_cp_normal': line.product_id.name,
                'credit': round((amount / qty_po_origin) * qty_po_done),
                'debit': 0
            })]
            if move.product_id.type in ('product', 'consu'):
                svl_values.append((0, 0, {
                    'value': round((amount / qty_po_origin) * qty_po_done),
                    'unit_cost': amount / qty_po_origin,
                    'quantity': 0,
                    'remaining_qty': 0,
                    'description': f"{self.name} - {line.product_id.name}",
                    'product_id': move.product_id.id,
                    'company_id': self.env.company.id,
                    'stock_move_id': move.id
                }))

                if not move.product_id.categ_id.property_stock_valuation_account_id:
                    raise ValidationError("Bạn chưa cấu hình tài khoản nhập kho trong danh mục nhóm sản phẩm của sản phẩm %s" % move.product_id.display_name)

                move_lines += [(0, 0, {
                    'sequence': 2,
                    'account_id': move.product_id.categ_id.property_stock_valuation_account_id.id,
                    'product_id': move.product_id.id,
                    'name': product_tax.name,
                    'text_check_cp_normal': line.product_id.name,
                    'credit': 0.0,
                    'debit': round((amount / qty_po_origin) * qty_po_done),
                })]

            move_value.update({
                'stock_valuation_layer_ids': svl_values,
                'line_ids': move_lines
            })

            move_values.append(move_value)

        return move_values

    def view_move_tax_entry(self):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_account_moves_all")
        domain = ['|', ('move_id', 'in', (self.move_ids).stock_valuation_layer_ids.mapped('account_move_id').ids), ('move_id.stock_move_id', 'in', self.move_ids.ids)]
        return dict(action, domain=domain)

    def create_expense_entries(self, po):
        self.ensure_one()
        results = self.env['account.move']
        if self.state != 'done' or not po:
            return results
        entries_values = []
        for move in self.move_ids:
            if move.product_id.type not in ('product', 'consu'):
                continue
            product_po = po.order_line.filtered(lambda x: x.product_id == move.product_id)
            po_total_qty = sum(product_po.mapped('product_qty'))
            amount_rate = sum(product_po.mapped('total_vnd_amount')) / sum(po.order_line.mapped('total_vnd_amount'))
            for expense in po.cost_line:
                expense_vnd_amount = round(expense.vnd_amount * amount_rate, 0)
                sp_total_qty = move.quantity_done

                if sp_total_qty == 0:
                    continue

                if not expense.product_id.categ_id.property_stock_account_input_categ_id:
                    raise ValidationError("Bạn chưa cấu hình tài khoản nhập kho trong danh mục nhóm sản phẩm của sản phẩm %s" % expense.product_id.display_name)

                entries_values += [{
                    'ref': f"{self.name}",
                    'purchase_type': po.purchase_type,
                    'move_type': 'entry',
                    'x_entry_types': 'entry_cost',
                    'reference': po.name,
                    'exchange_rate': po.exchange_rate,
                    'date': datetime.utcnow(),
                    'invoice_payment_term_id': po.payment_term_id.id,
                    'invoice_date_due': po.date_planned,
                    'restrict_mode_hash_table': False,
                    'stock_valuation_layer_ids': [(0, 0, {
                        'value': expense_vnd_amount / po_total_qty * move.quantity_done,
                        'unit_cost': expense_vnd_amount / po_total_qty,
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
                        'credit': round(expense_vnd_amount / po_total_qty * sp_total_qty),
                        'debit': 0
                    }),
                    (0, 0, {
                         'sequence': 2,
                         'account_id': move.product_id.categ_id.property_stock_valuation_account_id.id,
                         'product_id': move.product_id.id,
                         'name': move.product_id.name,
                         'text_check_cp_normal': move.product_id.name,
                         'credit': 0,
                         'debit': round(expense_vnd_amount / po_total_qty * move.quantity_done)
                    })],
                }]
                for value in entries_values:
                    debit = 0.0
                    for line in value['invoice_line_ids'][1:]:
                        if debit:
                            line[-1]['debit'] += round(debit)
                            debit = 0.0
                        else:
                            debit = line[-1]['debit'] - round(line[-1]['debit'])
                            line[-1]['debit'] = round(line[-1]['debit'])
        results = results.create(entries_values)
        results._post()
        return results

    # Xử lý nhập kho sinh bút toán ở tab chi phí po theo số lượng nhập kho
    def create_invoice_po_cost(self, po, record):
        data_in_line = po.order_line
        data_ex_line = po.exchange_rate_line_ids
        data_co_line = po.cost_line
        data_st_line = record.move_ids_without_package
        list_cp_after_tax = []
        list_money = []
        tax_amount = []
        special_amount = []
        total_vnd_exchange = []
        if record.state == 'done':
            for po_l, pk_l, ex_l in zip(data_in_line, data_st_line, data_ex_line):
                if pk_l.picking_id.state == 'done':
                    if pk_l.quantity_done * po_l.price_unit != 0:
                        list_money.append((pk_l.quantity_done/po_l.product_qty * po_l.total_vnd_amount))
                    if ex_l.tax_amount:
                        tax_amount.append(ex_l.tax_amount)
                    if ex_l.special_consumption_tax_amount:
                        special_amount.append(ex_l.special_consumption_tax_amount)
                    if ex_l.total_vnd_exchange:
                        total_vnd_exchange.append(ex_l.total_vnd_exchange)
            total_money = sum(list_money)
            total_tax_amount = sum(tax_amount)
            total_special_amount = sum(special_amount)
            total_vnd_exchange = sum(total_vnd_exchange)
            for item, exchange, total, pk_l in zip(data_in_line, data_ex_line, list_money, data_st_line):
                if item.product_id.categ_id and item.product_id.categ_id.with_company(record.company_id).property_stock_valuation_account_id:
                    account_1561 = item.product_id.categ_id.with_company(record.company_id).property_stock_valuation_account_id.id
                else:
                    raise ValidationError(('Bạn chưa cấu hình tài khoản định giá tồn kho trong danh mục sản phẩm của sản phẩm %s!') % item.product_id.name)
                for rec in data_co_line:
                    if rec.product_id.categ_id and rec.product_id.categ_id.with_company(record.company_id).property_stock_valuation_account_id:
                        account_acc = rec.product_id.categ_id.with_company(record.company_id).property_stock_account_input_categ_id.id
                    else:
                        raise ValidationError(('Bạn chưa cấu hình nhập kho trong danh mục sản phẩm của %s!') % rec.product_id.name)
                    if rec.vnd_amount:
                        if not rec.is_check_pre_tax_costs:
                            values = (((exchange.total_vnd_exchange + exchange.tax_amount + exchange.special_consumption_tax_amount) * pk_l.quantity_done / item.product_qty) / ((
                                                              total_vnd_exchange + total_tax_amount + total_special_amount) * pk_l.quantity_done / item.product_qty)) * rec.vnd_amount * pk_l.quantity_done / item.product_qty
                            debit_cp = (0, 0, {
                                'sequence': 1,
                                'account_id': account_1561,
                                'product_id': item.product_id.id,
                                'name': item.product_id.name,
                                'text_check_cp_normal': rec.product_id.name,
                                'debit': values,
                                'credit': 0,
                            })
                            credit_cp = (0, 0, {
                                'sequence': 99991,
                                'account_id': account_acc,
                                'product_id': rec.product_id.id,
                                'name': rec.product_id.name,
                                'text_check_cp_normal': rec.product_id.name,
                                'debit': 0,
                                'credit': values,
                            })
                            lines_cp_after_tax = [credit_cp, debit_cp]
                            list_cp_after_tax.extend(lines_cp_after_tax)
                        else:
                            debit_cp = (0, 0, {
                                'sequence': 1,
                                'account_id': account_1561,
                                'product_id': item.product_id.id,
                                'name': item.product_id.name,
                                'text_check_cp_normal': rec.product_id.name,
                                'debit': total / total_money * (rec.vnd_amount * pk_l.quantity_done/item.product_qty),
                                'credit': 0,
                            })
                            credit_cp = (0, 0, {
                                'sequence': 99991,
                                'account_id': account_acc,
                                'product_id': rec.product_id.id,
                                'name': rec.product_id.name,
                                'text_check_cp_normal': rec.product_id.name,
                                'debit': 0,
                                'credit': total / total_money * (rec.vnd_amount * pk_l.quantity_done/item.product_qty),
                            })
                            lines_cp_before_tax = [credit_cp, debit_cp]
                            list_cp_after_tax.extend(lines_cp_before_tax)
            for rec in po.cost_line:
                separated_lists = {}
                invoice_line_ids = []
                target_items = rec.product_id.name
                for lines_cp_after_tax in list_cp_after_tax:
                    text_check_cp_normal = lines_cp_after_tax[2]['text_check_cp_normal']
                    if text_check_cp_normal in target_items:
                        if text_check_cp_normal in separated_lists:
                            separated_lists[text_check_cp_normal].append(lines_cp_after_tax)
                        else:
                            separated_lists[text_check_cp_normal] = [lines_cp_after_tax]
                new_lines_cp_after_tax = [lines for text_check, lines in separated_lists.items()]
                for sublist_lines_cp_after_tax in new_lines_cp_after_tax:
                    invoice_line_ids.extend(sublist_lines_cp_after_tax)
                merged_records_cp = {}
                for cp in invoice_line_ids:
                    key = (cp[2]['account_id'], cp[2]['name'], cp[2]['sequence'], cp[2]['product_id'], cp[2]['text_check_cp_normal'])
                    if key in merged_records_cp:
                        merged_records_cp[key]['debit'] += cp[2]['debit']
                        merged_records_cp[key]['credit'] += cp[2]['credit']
                    else:
                        merged_records_cp[key] = {
                            'sequence': cp[2]['sequence'],
                            'text_check_cp_normal': cp[2]['text_check_cp_normal'],
                            'account_id': cp[2]['account_id'],
                            'product_id': cp[2]['product_id'],
                            'name': cp[2]['name'],
                            'debit': cp[2]['debit'],
                            'credit': cp[2]['credit'],
                        }
                merged_records_list_cp = [(0, 0, record) for record in merged_records_cp.values()]
                if merged_records_list_cp:
                    entry_cp = self.env['account.move'].create({
                        'ref': f"{record.name} - {rec.product_id.name}",
                        'purchase_type': po.purchase_type,
                        'move_type': 'entry',
                        'x_entry_types': 'entry_cost',
                        'reference': po.name,
                        'exchange_rate': po.exchange_rate,
                        'date': datetime.now(),
                        'invoice_payment_term_id': po.payment_term_id.id,
                        'invoice_date_due': po.date_planned,
                        'invoice_line_ids': merged_records_list_cp,
                        'restrict_mode_hash_table': False
                    })
                    entry_cp._post()

    # Xử lý nhập kho sinh bút toán ở tab thuế nhập khẩu po theo số lượng nhập kho
    def create_invoice_po_tax(self, po, record):
        list_nk = []
        list_db = []
        if record.state == 'done':
            for ex_l, pk_l in zip(po.exchange_rate_line_ids, record.move_ids_without_package):
                if ex_l.product_id.categ_id and ex_l.product_id.categ_id.with_company(record.company_id).property_stock_valuation_account_id:
                    account_1561 = ex_l.product_id.categ_id.with_company(record.company_id).property_stock_valuation_account_id.id
                else:
                    raise ValidationError(_('Bạn chưa cấu hình tài khoản định giá tồn kho của sản phẩm %s trong danh mục của sản phẩm đó!') % ex_l.product_id.name)
                if ex_l.product_qty <= 0 and pk_l.quantity_done <= 0:
                    raise ValidationError('Số lượng của sản phẩm hay số lương hoàn thành khi nhập kho phải lớn hơn 0')
                if not self.env.ref('forlife_purchase.product_import_tax_default').categ_id.property_stock_account_input_categ_id:
                    raise ValidationError("Bạn chưa cấu hình tài khoản nhập kho trong danh mục nhóm sản phẩm của sản phẩm tên là 'Thuế nhập khẩu'")
                if not self.env.ref('forlife_purchase.product_excise_tax_default').categ_id.property_stock_account_input_categ_id:
                    raise ValidationError("Bạn chưa cấu hình tài khoản nhập kho trong danh mục nhóm sản phẩm của sản phẩm tên là 'Thuế tiêu thụ đặc biệt'")
                if ex_l.tax_amount:
                    debit_nk = (0, 0, {
                        'sequence': 9,
                        'account_id': account_1561,
                        'name': ex_l.product_id.name,
                        'debit': (pk_l.quantity_done / ex_l.product_qty * ex_l.tax_amount),
                        'credit': 0,
                    })
                    credit_nk = (0, 0, {
                        'sequence': 99991,
                        'account_id': self.env.ref('forlife_purchase.product_import_tax_default').categ_id.property_stock_account_input_categ_id.id,
                        'name': self.env.ref('forlife_purchase.product_import_tax_default').name,
                        'debit': 0,
                        'credit': (pk_l.quantity_done / ex_l.product_qty * ex_l.tax_amount),
                    })
                    lines_nk = [debit_nk, credit_nk]
                    list_nk.extend(lines_nk)
                if ex_l.special_consumption_tax_amount:
                    debit_db = (0, 0, {
                        'sequence': 9,
                        'account_id': account_1561,
                        'name': ex_l.product_id.name,
                        'debit': (pk_l.quantity_done / ex_l.product_qty * ex_l.special_consumption_tax_amount),
                        'credit': 0,
                    })
                    credit_db = (0, 0, {
                        'sequence': 99991,
                        'account_id': self.env.ref('forlife_purchase.product_excise_tax_default').categ_id.property_stock_account_input_categ_id.id,
                        'name': self.env.ref('forlife_purchase.product_excise_tax_default').name,
                        'debit': 0,
                        'credit': (pk_l.quantity_done / ex_l.product_qty * ex_l.special_consumption_tax_amount),
                    })
                    lines_db = [debit_db, credit_db]
                    list_db.extend(lines_db)
            merged_records_tnk = {}
            merged_records_db = {}
            for tnk in list_nk:
                key = (tnk[2]['account_id'], tnk[2]['name'], tnk[2]['sequence'])
                if key in merged_records_tnk:
                    merged_records_tnk[key]['debit'] += tnk[2]['debit']
                    merged_records_tnk[key]['credit'] += tnk[2]['credit']
                else:
                    merged_records_tnk[key] = {
                        'sequence': tnk[2]['sequence'],
                        'account_id': tnk[2]['account_id'],
                        'name': tnk[2]['name'],
                        'debit': tnk[2]['debit'],
                        'credit': tnk[2]['credit'],
                    }
            merged_records_list_tnk = [(0, 0, record) for record in merged_records_tnk.values()]
            for db in list_db:
                key = (db[2]['account_id'], db[2]['name'], db[2]['sequence'])
                if key in merged_records_db:
                    merged_records_db[key]['debit'] += db[2]['debit']
                    merged_records_db[key]['credit'] += db[2]['credit']
                else:
                    merged_records_db[key] = {
                        'sequence': db[2]['sequence'],
                        'account_id': db[2]['account_id'],
                        'name': db[2]['name'],
                        'debit': db[2]['debit'],
                        'credit': db[2]['credit'],
                    }
            merged_records_list_db = [(0, 0, record) for record in merged_records_db.values()]
            if merged_records_list_tnk:
                entry_nk = self.env['account.move'].create({
                    'ref': f"{record.name} - {self.env.ref('forlife_purchase.product_import_tax_default').name}",
                    'purchase_type': po.purchase_type,
                    'move_type': 'entry',
                    'x_entry_types': 'entry_import_tax',
                    'reference': po.name,
                    'exchange_rate': po.exchange_rate,
                    'date': datetime.now(),
                    'invoice_payment_term_id': po.payment_term_id.id,
                    'invoice_date_due': po.date_planned,
                    'invoice_line_ids': merged_records_list_tnk,
                    'restrict_mode_hash_table': False
                })
                entry_nk._post()

            if merged_records_list_db:
                entry_db = self.env['account.move'].create({
                    'ref': f"{record.name} - {self.env.ref('forlife_purchase.product_excise_tax_default').name}",
                    'purchase_type': po.purchase_type,
                    'move_type': 'entry',
                    'x_entry_types': 'entry_special_consumption_tax',
                    'reference': po.name,
                    'exchange_rate': po.exchange_rate,
                    'date': datetime.now(),
                    'invoice_payment_term_id': po.payment_term_id.id,
                    'invoice_date_due': po.date_planned,
                    'invoice_line_ids': merged_records_list_db,
                    'restrict_mode_hash_table': False
                })
                entry_db._post()

    # Xử lý nhập kho sinh bút toán ở tab npl po theo số lượng nhập kho + sinh bút toán cho chi phí nhân công nội địa
    def create_invoice_npl(self, po, record):
        list_npls = []
        list_allowcation_npls = []
        list_line_xk = []
        cost_labor_internal_costs = []
        if record.state == 'done':
            move = False
            ### Tìm bản ghi Xuât Nguyên Phụ Liệu
            export_production_order = self.env['stock.location'].search([('company_id', '=', self.env.company.id),
                                                                         ('code', '=', 'X1201')
                                                                         ], limit=1)
            if not export_production_order.x_property_valuation_in_account_id:
                raise ValidationError('Bạn chưa có hoặc chưa cấu hình tài khoản trong lý do xuất nguyên phụ liệu \n Gợi ý: Tạo lý do trong cấu hình Lý do nhập khác và xuất khác có mã: X1201')
            else:
                if not export_production_order.reason_type_id:
                    raise ValidationError('Bạn chưa cấu hình loại lý do cho lý do nhập khác có mã: X1201')
                account_export_production_order = export_production_order.x_property_valuation_in_account_id
            for item, r in zip(po.order_line_production_order, record.move_ids_without_package):
                move = self.env['stock.move'].search(
                    [('purchase_line_id', '=', item.id), ('picking_id', '=', self.id)])
                material = self.env['purchase.order.line.material.line'].search([('purchase_order_line_id', '=', item.id)])

                if item.product_id.categ_id and item.product_id.categ_id.with_company(record.company_id).property_stock_valuation_account_id:
                    account_1561 = item.product_id.categ_id.with_company(record.company_id).property_stock_valuation_account_id.id
                else:
                    raise ValidationError(_("Bạn chưa cấu hình tài khoản định giá tồn kho trong danh mục sản phẩm của sản phẩm có tên %s") % item.product_id.name)

                debit_cost = 0
                for material_line in material:
                    if material_line.product_id.product_tmpl_id.x_type_cost_product in ('labor_costs', 'internal_costs'):
                        if not material_line.product_id.categ_id or not material_line.product_id.categ_id.with_company(record.company_id).property_stock_account_input_categ_id:
                            raise ValidationError(_("Bạn chưa cấu hình tài khoản nhập kho trong danh mực sản phẩm của %s") % material_line.product_id.name)
                        if material_line.price_unit > 0:
                            pbo = material_line.price_unit * r.quantity_done * material_line.production_line_product_qty / material_line.production_order_product_qty
                            credit_cp = (0, 0, {
                                'sequence': 99991,
                                'account_id': material_line.product_id.categ_id.with_company(record.company_id).property_stock_account_input_categ_id.id,
                                'product_id': material_line.product_id.id,
                                'name': material_line.product_id.name,
                                'text_check_cp_normal': item.product_id.name,
                                'debit': 0,
                                'credit': pbo,
                            })
                            cost_labor_internal_costs.append(credit_cp)
                            debit_cost += pbo
                    else:
                        list_line_xk.append((0, 0, {
                            'product_id': material_line.product_id.id,
                            'product_uom': material_line.uom.id,
                            'price_unit': material_line.price_unit,
                            'location_id': po.location_export_material_id.id,
                            'location_dest_id': export_production_order.id,
                            'product_uom_qty': r.quantity_done / item.purchase_quantity * material_line.product_qty,
                            'quantity_done': r.quantity_done / item.purchase_quantity * material_line.product_qty,
                            'amount_total': material_line.price_unit * material_line.product_qty,
                            'reason_id': export_production_order.id,
                        }))
                        #tạo bút toán npl ở bên bút toán sinh với khi nhập kho khác với phiếu xuất npl
                        if item.product_id.id == material_line.purchase_order_line_id.product_id.id:
                            if material_line.product_id.standard_price > 0:
                                debit_npl = (0, 0, {
                                    'sequence': 9,
                                    'account_id': account_export_production_order.id,
                                    'name': account_export_production_order.name,
                                    'debit': ((r.quantity_done / item.product_qty * material_line.product_qty) * material_line.product_id.standard_price),
                                    'credit': 0,
                                })
                                credit_npl = (0, 0, {
                                    'sequence': 99991,
                                    'account_id': material_line.product_id.categ_id.with_company(record.company_id).property_stock_valuation_account_id.id,
                                    'name': material_line.product_id.name,
                                    'debit': 0,
                                    'credit': ((r.quantity_done / item.product_qty * material_line.product_qty) * material_line.product_id.standard_price),
                                })
                                lines_npl = [debit_npl, credit_npl]
                                list_npls.extend(lines_npl)

                                #xử lý phân bổ nguyên vật liệu
                                debit_allowcation_npl = (0, 0, {
                                    'sequence': 1,
                                    'account_id': account_1561,
                                    'name': item.product_id.name,
                                    'debit': ((r.quantity_done / item.product_qty * material_line.product_qty) * material_line.product_id.standard_price),
                                    'credit': 0,
                                })

                                credit_allowcation_npl = (0, 0, {
                                    'sequence': 2,
                                    'account_id': account_export_production_order.id,
                                    'name': account_export_production_order.name,
                                    'debit': 0,
                                    'credit': ((r.quantity_done / item.product_qty * material_line.product_qty) * material_line.product_id.standard_price),
                                })
                                list_allowcation_npls.extend([debit_allowcation_npl, credit_allowcation_npl])

                if debit_cost > 0:
                    debit_cp = (0, 0, {
                        'sequence': 9,
                        'account_id': account_1561,
                        'product_id': item.product_id.id,
                        'name': item.product_id.name,
                        'text_check_cp_normal': item.product_id.name,
                        'debit': debit_cost,
                        'credit': 0,
                    })
                    cost_labor_internal_costs.append(debit_cp)
                    separated_lists = {}
                    invoice_line_ids = []
                    target_items = item.product_id.name
                    for lines_new in cost_labor_internal_costs:
                        text_check_cp_normal = lines_new[2]['text_check_cp_normal']
                        if text_check_cp_normal in target_items:
                            if text_check_cp_normal in separated_lists:
                                separated_lists[text_check_cp_normal].append(lines_new)
                            else:
                                separated_lists[text_check_cp_normal] = [lines_new]
                    new_lines_cp_after_tax = [lines for text_check, lines in separated_lists.items()]
                    for sublist_lines_cp_after_tax in new_lines_cp_after_tax:
                        invoice_line_ids.extend(sublist_lines_cp_after_tax)


                    qty_po_done = sum(move.mapped('quantity_done'))
                    svl_values = []
                    svl_values.append((0, 0, {
                        'value': debit_cost,
                        'unit_cost': debit_cost / qty_po_done,
                        'quantity': 0,
                        'remaining_qty': 0,
                        'description': f"{self.name} - {item.product_id.name}",
                        'product_id': move.product_id.id,
                        'company_id': self.env.company.id,
                        'stock_move_id': move.id
                    }))
                    entry_cp = self.env['account.move'].create({
                        'ref': f"{record.name} - Chi phí nhân công thuê ngoài/nội bộ - {target_items}",
                        'purchase_type': po.purchase_type,
                        'move_type': 'entry',
                        'x_entry_types': 'entry_cost_labor',
                        'reference': po.name,
                        'exchange_rate': po.exchange_rate,
                        'date': datetime.now(),
                        'invoice_payment_term_id': po.payment_term_id.id,
                        'invoice_date_due': po.date_planned,
                        'invoice_line_ids': invoice_line_ids,
                        'restrict_mode_hash_table': False,
                        'stock_valuation_layer_ids': svl_values
                    })
                    entry_cp._post()


            if list_npls:
                merged_records_npl = {}
                for npl in list_npls:
                    key = (npl[2]['account_id'], npl[2]['name'], npl[2]['sequence'])
                    if key in merged_records_npl:
                        merged_records_npl[key]['debit'] += npl[2]['debit']
                        merged_records_npl[key]['credit'] += npl[2]['credit']
                    else:
                        merged_records_npl[key] = {
                            'sequence': npl[2]['sequence'],
                            'account_id': npl[2]['account_id'],
                            'name': npl[2]['name'],
                            'debit': npl[2]['debit'],
                            'credit': npl[2]['credit'],
                        }
                merged_records_list_npl = [(0, 0, record) for record in merged_records_npl.values()]
                if merged_records_list_npl:
                    entry_npls = self.env['account.move'].create({
                        'ref': f"{record.name} - Nguyên phụ liệu",
                        'purchase_type': po.purchase_type,
                        'move_type': 'entry',
                        'x_entry_types': 'entry_material',
                        'reference': po.name,
                        'exchange_rate': po.exchange_rate,
                        'date': datetime.now(),
                        'invoice_payment_term_id': po.payment_term_id.id,
                        'invoice_date_due': po.date_planned,
                        'invoice_line_ids': merged_records_list_npl,
                        'restrict_mode_hash_table': False
                    })
                    entry_npls._post()
                    if record.state == 'done':
                        master_xk = self.create_xk_picking(po, record, list_line_xk, export_production_order, entry_npls)

            if list_allowcation_npls:
                merged_records_allowcation_npl = {}
                total_npl_amount = 0
                for allowcation_npl in list_allowcation_npls:
                    key = (
                    allowcation_npl[2]['account_id'], allowcation_npl[2]['name'], allowcation_npl[2]['sequence'])
                    if key in merged_records_allowcation_npl:
                        merged_records_allowcation_npl[key]['debit'] += allowcation_npl[2]['debit']
                        merged_records_allowcation_npl[key]['credit'] += allowcation_npl[2]['credit']
                    else:
                        merged_records_allowcation_npl[key] = {
                            'sequence': allowcation_npl[2]['sequence'],
                            'account_id': allowcation_npl[2]['account_id'],
                            'name': allowcation_npl[2]['name'],
                            'debit': allowcation_npl[2]['debit'],
                            'credit': allowcation_npl[2]['credit'],
                        }
                    total_npl_amount += allowcation_npl[2]['debit']
                merged_records_list_allowcation_npl = [(0, 0, record) for record in
                                                       merged_records_allowcation_npl.values()]
                if merged_records_list_allowcation_npl:
                    qty_po_done = sum(move.mapped('quantity_done'))
                    svl_allowcation_values = []
                    svl_allowcation_values.append((0, 0, {
                        'value': total_npl_amount,
                        'unit_cost': total_npl_amount / qty_po_done,
                        'quantity': 0,
                        'remaining_qty': 0,
                        'description': f"{self.name} - {item.product_id.name}",
                        'product_id': move.product_id.id,
                        'company_id': self.env.company.id,
                        'stock_move_id': move.id
                    }))
                    entry_allowcation_npls = self.env['account.move'].create({
                        'ref': f"{record.name} - Phân bổ nguyên phụ liệu",
                        'purchase_type': po.purchase_type,
                        'move_type': 'entry',
                        # 'x_entry_types': 'entry_material',
                        'reference': po.name,
                        'exchange_rate': po.exchange_rate,
                        'date': datetime.now(),
                        'invoice_payment_term_id': po.payment_term_id.id,
                        'invoice_date_due': po.date_planned,
                        'invoice_line_ids': merged_records_list_allowcation_npl,
                        'restrict_mode_hash_table': False,
                        'stock_valuation_layer_ids': svl_allowcation_values
                    })
                    entry_allowcation_npls._post()

    ###tự động tạo phiếu xuất khác và hoàn thành khi nhập kho hoàn thành
    def create_xk_picking(self, po, record, list_line_xk, export_production_order, account_move=None):
        company_id = self.env.company.id
        picking_type_out = self.env['stock.picking.type'].search([
            ('code', '=', 'outgoing'),
            ('company_id', '=', company_id)], limit=1)
        master_xk = {
            "is_locked": True,
            "immediate_transfer": False,
            'location_id': po.location_export_material_id.id,
            # 'reason_type_id': reason_type_6.id,
            'location_dest_id': export_production_order.id,
            'scheduled_date': datetime.now(),
            'origin': po.name,
            'other_export': True,
            'state': 'assigned',
            'picking_type_id': picking_type_out.id,
            'move_ids_without_package': list_line_xk
        }
        xk_picking = self.env['stock.picking'].with_context({'skip_immediate': True, 'endloop': True}).create(master_xk)
        xk_picking.button_validate()
        if account_move:
            xk_picking.write({'account_xk_id': account_move.id})
        record.write({'picking_xk_id': xk_picking.id})
        return xk_picking
