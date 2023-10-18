from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


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
            'res_id': self.account_xk_id.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': domain
        }

    def action_cancel(self):
        for rec in self:
            rec.back_data_picking_account_xk()
        return super(StockPicking, self).action_cancel()

    def action_back_to_draft(self):
        for rec in self:
            rec.back_data_picking_account_xk()
        return super(StockPicking, self).action_back_to_draft()

    def back_data_picking_account_xk(self):
        if self.picking_xk_id:
            self.picking_xk_id.action_cancel()
            self.picking_xk_id.action_back_to_draft()
            self.picking_xk_id.unlink()
        if self.account_xk_id:
            self.account_xk_id.button_draft()
            self.account_xk_id.button_cancel()
            self.account_xk_id.unlink()

    def check_quant_goods_import(self, po):
        self.ensure_one()
        product_have_qty_done = self.move_ids_without_package.filtered(lambda x: x.quantity_done).product_id
        material_line_ids = po.order_line_production_order.filtered(lambda x: x.product_id.id in product_have_qty_done.ids).purchase_order_line_material_line_ids
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

    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        if self._context.get('endloop'):
            return True
        for record in self:
            po = record.purchase_id
            if not po:
                continue
            if po.is_inter_company == False and not po.is_return and not record.move_ids[0]._is_purchase_return():
                ## check npl tồn:
                self.check_quant_goods_import(po)
                _context = {
                    'pk_no_input_warehouse': False,
                }
                if po.type_po_cost == 'tax':
                    # tạo bút toán định giá tồn kho với thuế nhập khẩu và thuế đặc biệt
                    if po and po.exchange_rate_line_ids:
                        move_import_tax_values = record.prepare_move_svl_value_with_tax_po(po, 'import') # thuế nhập khẩu
                        move_special_tax_values = record.prepare_move_svl_value_with_tax_po(po, 'special') # thuế tiêu thụ đặc biệt
                        move_values = move_import_tax_values + move_special_tax_values
                        moves = self.env['account.move'].create(move_values)
                        if moves:
                            moves._post()
                if po.cost_line:
                    record.create_expense_entries(po)
                # Tạo nhập khác xuất khác khi nhập kho
                if po.order_line_production_order and not po.is_inter_company:
                    npl = self.create_invoice_npl(po, record)
                account_move = self.env['account.move'].search([('stock_move_id', 'in', self.move_ids.ids)])
                account_move.update({
                    'currency_id': po.currency_id.id,
                    'exchange_rate': po.exchange_rate
                })
            for rec in record.move_ids:
                if rec.product_id.categ_id.category_type_id.code not in ('2','3','4'):
                    continue
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
        return res

    def prepare_move_svl_value_with_tax_po(self, po, tax_type):
        if not po.exchange_rate_line_ids or len(po.exchange_rate_line_ids) <= 0:
            return []
        move_values = []
        journal_id = self.env['account.journal'].search([('code', '=', 'EX02'), ('type', '=', 'general')], limit=1).id
        if not journal_id:
            raise ValidationError("Không tìm thấy sổ nhật ký có mã 'EX02'. Vui lòng cấu hình thêm!")
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
                'ref': f"{self.name}",
                'purchase_type': po.purchase_type,
                'move_type': 'entry',
                'reference': po.name,
                'stock_move_id': move.id,
                'journal_id': journal_id,
                'exchange_rate': po.exchange_rate,
                'date': (self.date_done + timedelta(hours=7)).date(),
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
                if move.product_id.cost_method == 'average':
                    self.add_cost_product(move.product_id, round((amount / qty_po_origin) * qty_po_done))

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
                sp_total_qty = move.quantity_done
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
                    'date': (self.date_done + timedelta(hours=7)).date(),
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
                        'credit': round(unit_cost * sp_total_qty),
                        'debit': 0
                    }),
                    (0, 0, {
                         'sequence': 2,
                         'account_id': move.product_id.categ_id.property_stock_valuation_account_id.id,
                         'product_id': move.product_id.id,
                         'name': move.product_id.name,
                         'text_check_cp_normal': move.product_id.name,
                         'credit': 0,
                         'debit': round(unit_cost * sp_total_qty)
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
                if move.product_id.cost_method == 'average':
                    self.add_cost_product(move.product_id, round(unit_cost * sp_total_qty))
        results = results.create(entries_values)
        results._post()
        return results
    
    #TienNQ add recompute standard_price in product
    def add_cost_product(self, product, cost):
        if not float_is_zero(product.quantity_svl, precision_rounding=product.uom_id.rounding):
            product.with_company(self.company_id).sudo().with_context(disable_auto_svl=True).standard_price += cost / product.quantity_svl


    # Xử lý nhập kho sinh bút toán ở tab npl po theo số lượng nhập kho + sinh bút toán cho chi phí nhân công nội địa
    def create_invoice_npl(self, po, record):
        list_npls = []
        list_allowcation_npls = []
        list_line_xk = []
        cost_labor_internal_costs = []
        journal_id = self.env['account.journal'].search([('code', '=', 'EX02'), ('type', '=', 'general')], limit=1).id
        if not journal_id:
            raise ValidationError("Không tìm thấy sổ nhật ký có mã 'EX02'. Vui lòng cấu hình thêm!")
        if record.state == 'done':
            ### Tìm bản ghi Xuât Nguyên Phụ Liệu
            export_production_order = self.env['stock.location'].search([('company_id', '=', self.env.company.id), ('code', '=', 'X1201')], limit=1)
            if not export_production_order.x_property_valuation_in_account_id:
                raise ValidationError('Bạn chưa có hoặc chưa cấu hình tài khoản trong lý do xuất nguyên phụ liệu \n Gợi ý: Tạo lý do trong cấu hình Lý do nhập khác và xuất khác có mã: X1201')
            else:
                if not export_production_order.reason_type_id:
                    raise ValidationError('Bạn chưa cấu hình loại lý do cho lý do nhập khác có mã: X1201')
                account_export_production_order = export_production_order.x_property_valuation_in_account_id
            for r in record.move_ids_without_package:
                # move = self.env['stock.move'].search([('purchase_line_id', '=', item.id), ('picking_id', '=', record.id)])
                if not r.purchase_line_id.x_check_npl:
                    continue
                item = r.purchase_line_id
                move = record.move_ids.filtered(lambda x: x.purchase_line_id.id == item.id)
                if not move:
                    continue
                qty_po_done = sum(move.mapped('quantity_done'))
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
                            pbo = round(material_line.price_unit * r.quantity_done * material_line.production_line_product_qty / material_line.production_order_product_qty)
                            credit_cp = (0, 0, {
                                'sequence': 99991,
                                'account_id': material_line.product_id.categ_id.with_company(record.company_id).property_stock_account_input_categ_id.id,
                                'product_id': move.product_id.id,
                                'name': material_line.product_id.name,
                                'text_check_cp_normal': move.product_id.name,
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
                            'product_uom_qty': r.quantity_done / item.product_qty * material_line.product_qty,
                            'quantity_done': r.quantity_done / item.product_qty * material_line.product_qty,
                            'amount_total': material_line.price_unit * material_line.product_qty,
                            'reason_id': export_production_order.id,
                        }))
                        #tạo bút toán npl ở bên bút toán sinh với khi nhập kho khác với phiếu xuất npl
                        if item.product_id.id == material_line.purchase_order_line_id.product_id.id:
                            if material_line.product_id.standard_price > 0:
                                value = round((r.quantity_done / item.product_qty * material_line.product_qty) * material_line.product_id.standard_price)
                                #xử lý phân bổ nguyên vật liệu
                                debit_allowcation_npl = (0, 0, {
                                    'sequence': 1,
                                    'product_id': move.product_id.id,
                                    'account_id': account_1561,
                                    'name': item.product_id.name,
                                    'debit': value,
                                    'credit': 0,
                                })

                                credit_allowcation_npl = (0, 0, {
                                    'sequence': 2,
                                    'product_id': move.product_id.id,
                                    'account_id': account_export_production_order.id,
                                    'name': account_export_production_order.name,
                                    'debit': 0,
                                    'credit': value,
                                })
                                list_allowcation_npls.extend([debit_allowcation_npl, credit_allowcation_npl])

                if debit_cost > 0:
                    debit_cp = (0, 0, {
                        'sequence': 9,
                        'account_id': account_1561,
                        'product_id': move.product_id.id,
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
                    if move.product_id.cost_method == 'average':
                        self.add_cost_product(move.product_id, debit_cost)
                    entry_cp = self.env['account.move'].create({
                        'ref': f"{record.name}",
                        'purchase_type': po.purchase_type,
                        'move_type': 'entry',
                        'journal_id': journal_id,
                        'x_entry_types': 'entry_cost_labor',
                        'reference': po.name,
                        'exchange_rate': po.exchange_rate,
                        'date': (record.date_done + timedelta(hours=7)).date(),
                        'invoice_payment_term_id': po.payment_term_id.id,
                        'invoice_date_due': po.date_planned,
                        'stock_move_id': move.id,
                        'invoice_line_ids': invoice_line_ids,
                        'restrict_mode_hash_table': False,
                        'stock_valuation_layer_ids': svl_values
                    })
                    entry_cp._post()

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
                                'product_id': allowcation_npl[2]['product_id'],
                                'account_id': allowcation_npl[2]['account_id'],
                                'name': allowcation_npl[2]['name'],
                                'debit': allowcation_npl[2]['debit'],
                                'credit': allowcation_npl[2]['credit'],
                            }
                        total_npl_amount += allowcation_npl[2]['debit']
                    merged_records_list_allowcation_npl = [(0, 0, record) for record in merged_records_allowcation_npl.values()]
                    if merged_records_list_allowcation_npl:
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
                        if move.product_id.cost_method == 'average':
                            self.add_cost_product(move.product_id, total_npl_amount)
                        entry_allowcation_npls = self.env['account.move'].create({
                            'ref': f"{record.name}",
                            'purchase_type': po.purchase_type,
                            'move_type': 'entry',
                            'journal_id': journal_id,
                            'x_entry_types': 'entry_material',
                            'reference': po.name,
                            'exchange_rate': po.exchange_rate,
                            'date': (record.date_done + timedelta(hours=7)).date(),
                            'invoice_payment_term_id': po.payment_term_id.id,
                            'invoice_date_due': po.date_planned,
                            'invoice_line_ids': merged_records_list_allowcation_npl,
                            'restrict_mode_hash_table': False,
                            'stock_move_id': move.id,
                            'stock_valuation_layer_ids': svl_allowcation_values
                        })
                        entry_allowcation_npls._post()

            # tạo phiếu xuất NPL
            if list_line_xk:
                self.create_xk_picking(po, record, list_line_xk, export_production_order)

    ###tự động tạo phiếu xuất khác và hoàn thành khi nhập kho hoàn thành
    def create_xk_picking(self, po, record, list_line_xk, export_production_order, account_move=None):
        company_id = self.env.company.id
        picking_type_out = self.env['stock.picking.type'].search([('code', '=', 'outgoing'), ('company_id', '=', company_id)], limit=1)
        master_xk = {
            "is_locked": True,
            "immediate_transfer": False,
            'location_id': po.location_export_material_id.id,
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
