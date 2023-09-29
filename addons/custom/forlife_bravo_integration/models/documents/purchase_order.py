# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class AccountMovePurchaseAsset(models.Model):
    _inherit = 'account.move'

    def bravo_get_purchase_asset_service_values(self, is_reversed=False):
        res = []
        columns = self.bravo_get_purchase_asset_service_columns()
        employees = self.env['res.utility'].get_multi_employee_by_list_uid(self.user_id.ids + self.env.user.ids)
        for record in self:
            user_id = str(record.user_id.id) or str(self._uid)
            employee = employees.get(user_id) or {}
            res.extend(record.bravo_get_purchase_asset_service_value(is_reversed, employee.get('code')))
        return columns, res

    @api.model
    def bravo_get_purchase_asset_service_columns(self):
        return [
            "CompanyCode", "Stt", "DocCode", "DocNo", "DocDate", "CurrencyCode", "ExchangeRate", "CustomerCode",
            "CustomerName", "Address", "Description", "AtchDocDate", "AtchDocNo", "TaxRegName", "TaxRegNo",
            "EmployeeCode", "IsTransfer", "CreditAccount", "DueDate", "IsCompany", "BuiltinOrder",
            "ItemCode", "ItemName", "UnitPurCode", "DebitAccount", "Quantity9", "ConvertRate9", "Quantity", "PriceUnit",
            "OriginalPriceUnit", "Discount", "OriginalDiscount", "OriginalUnitCost", "UnitCost", "OriginalAmount",
            "Amount", "TaxCode", "OriginalAmount3", "Amount3", "IsPromotions",
            "DebitAccount3", "CreditAccount3", "DocNo_PO", "RowId",
            "DocNo_WO", "DeptCode", "AssetCode", "ExpenseCatgCode", "ProductCode", "JobCode",
        ]

    def bravo_get_purchase_asset_service_value(self, is_reversed, employee_code):
        self.ensure_one()
        values = []
        journal_lines = self.line_ids
        invoice_lines = self.invoice_line_ids
        partner = self.partner_id
        is_partner_group_1 = partner.group_id == \
                             self.env.ref('forlife_pos_app_member.partner_group_1', raise_if_not_found=False)
        # the move has only one vendor -> all invoice lines will have the same partner -> same payable account
        journal_tax_lines = journal_lines.filtered(lambda l: l.tax_line_id)
        tax_line = journal_tax_lines and journal_tax_lines[0]
        payable_lines = journal_lines - invoice_lines - journal_tax_lines
        payable_line = payable_lines and payable_lines[0]
        payable_account_code = payable_line.account_id.code
        exchange_rate = self.exchange_rate

        journal_value = {
            "CompanyCode": self.company_id.code or None,
            "Stt": self.name or None,
            "DocCode": "XT" if is_reversed else ("NK" if is_partner_group_1 else "NM"),
            "DocNo": self.name or None,
            "DocDate": self.date or None,
            "CurrencyCode": self.currency_id.name or None,
            "ExchangeRate": exchange_rate or None,
            "CustomerCode": partner.ref or None,
            "CustomerName": partner.name or None,
            "Address": partner.contact_address_complete or None,
            "Description": self.invoice_description or None,
            "AtchDocDate": self.invoice_date or None,
            "AtchDocNo": self.number_bills or None,
            "TaxRegName": partner.name or None,
            "TaxRegNo": partner.vat or None,
            "EmployeeCode": employee_code or None,
            "IsTransfer": 1 if self.is_tc else 0,
            "CreditAccount": payable_account_code or None,
            "DueDate": self.invoice_date_due or None,
            "IsCompany": (self.x_root == "Intel" and 1) or (self.x_root == "Winning" and 2) or 3,
        }

        for idx, invoice_line in enumerate(invoice_lines, start=1):
            purchase_order_line = invoice_line.purchase_line_id
            product = invoice_line.product_id
            discount_amount = invoice_line.discount
            quantity = invoice_line.quantity
            journal_value_line = journal_value.copy()
            expense_code = (product.barcode or '')[1:]
            valid_expense_code = self.env['expense.item'].search(
                [('code', '=', expense_code), ('company_id', '=', self.company_id.id)], limit=1)
            journal_value_line.update({
                "BuiltinOrder": idx or None,
                "ItemCode": product.barcode or None,
                "ItemName": product.name or None,
                "UnitPurCode": purchase_order_line.purchase_uom.code or None,
                "DebitAccount": invoice_line.account_id.code or None,
                "Quantity9": invoice_line.quantity,
                "ConvertRate9": 1,
                "Quantity": invoice_line.quantity,
                "PriceUnit": invoice_line.price_unit * exchange_rate,
                "OriginalPriceUnit": invoice_line.price_unit,
                "Discount": discount_amount / (quantity * exchange_rate) if quantity else 0,
                "OriginalDiscount": discount_amount / quantity if quantity else 0,
                "OriginalUnitCost": invoice_line.price_unit - (discount_amount / quantity if quantity else 0),
                "UnitCost": (invoice_line.price_unit - (discount_amount / quantity if quantity else 0)) * exchange_rate,
                "OriginalAmount": invoice_line.price_subtotal,
                "Amount": invoice_line.price_subtotal * exchange_rate,
                "IsPromotions": 1 if invoice_line.promotions else 0,
                "DocNo_PO": self.reference or None,
                "JobCode": invoice_line.occasion_code_id.code or None,
                "RowId": invoice_line.id or None,
                "DocNo_WO": invoice_line.work_order.code or None,
                "DeptCode": invoice_line.analytic_account_id.code or None,
                "AssetCode": invoice_line.asset_id.code if (
                        invoice_line.asset_id and invoice_line.asset_id.type in ("CCDC", "TSCD")) else None,
                "ExpenseCatgCode": expense_code if valid_expense_code else None,
                "ProductCode": invoice_line.asset_id.code if (
                        invoice_line.asset_id and invoice_line.asset_id.type == "XDCB") else None,
                "TaxCode": tax_line.tax_line_id.code or None,
                "OriginalAmount3": invoice_line.tax_amount,
                "Amount3": invoice_line.tax_amount * exchange_rate,
                "DebitAccount3": tax_line.account_id.code,
                "CreditAccount3": payable_account_code
            })
            if is_reversed:
                reversed_account_values = {
                    "DebitAccount": journal_value_line.get('CreditAccount'),
                    "CreditAccount": journal_value_line.get('DebitAccount'),
                    "DebitAccount3": journal_value_line.get('CreditAccount3'),
                    "CreditAccount3": journal_value_line.get('DebitAccount3'),
                }
                journal_value_line.update(reversed_account_values)

            values.append(journal_value_line)

        return values


class AccountMovePurchaseProduct(models.Model):
    _inherit = 'account.move'

    def bravo_get_purchase_product_values(self, is_reversed=False):
        res = []
        columns = self.bravo_get_purchase_product_columns()
        employees = self.env['res.utility'].get_multi_employee_by_list_uid(self.user_id.ids + self.env.user.ids)
        for record in self:
            user_id = str(record.user_id.id) or str(self._uid)
            employee = employees.get(user_id) or {}
            res.extend(record.bravo_get_purchase_product_value(is_reversed, employee.get('code')))
        return columns, res

    @api.model
    def bravo_get_purchase_product_columns(self):
        return [
            "CompanyCode", "Stt", "DocCode", "DocNo", "DocDate", "CurrencyCode", "ExchangeRate", "CustomerCode",
            "CustomerName", "Address", "Description", "AtchDocDate", "AtchDocNo", "TaxRegName", "TaxRegNo",
            "AtchDocFormNo", "AtchDocSerialNo", "EmployeeCode", "IsTransfer", "DueDate", "BuiltinOrder", "DebitAccount",
            "CreditAccount", "DebitAccount3", "CreditAccount3", "TaxCode", "OriginalAmount", "Amount",
            "OriginalAmount3", "Amount3", "JobCode", "RowId", "DeptCode", "DocNo_WO", "DocNo_PO",
        ]

    def bravo_get_purchase_product_value(self, is_reversed, employee_code):
        self.ensure_one()
        values = []
        journal_lines = self.line_ids
        invoice_lines = self.invoice_line_ids
        partner = self.partner_id
        # the move has only one vendor -> all invoice lines will have the same partner -> same payable account
        journal_tax_lines = journal_lines.filtered(lambda l: l.tax_line_id)
        # get only one tax line (assume that all products with the same taxes)
        tax_line = journal_tax_lines and journal_tax_lines[0]
        payable_lines = journal_lines - invoice_lines - journal_tax_lines
        payable_line = payable_lines and payable_lines[0]
        payable_account_code = payable_line.account_id.code
        exchange_rate = self.exchange_rate

        journal_value = {
            "CompanyCode": self.company_id.code or None,
            "Stt": self.name or None,
            "DocCode": "BT",
            "DocNo": self.name or None,
            "DocDate": self.date or None,
            "CurrencyCode": self.currency_id.name or None,
            "ExchangeRate": exchange_rate,
            "CustomerCode": partner.ref or None,
            "CustomerName": partner.name or None,
            "Address": partner.contact_address_complete or None,
            "Description": self.invoice_description or None,
            "AtchDocDate": self.invoice_date or None,
            "AtchDocNo": self.number_bills or None,
            "TaxRegName": partner.name or None,
            "TaxRegNo": partner.vat or None,
            "EmployeeCode": employee_code or None,
            "IsTransfer": 1 if self.is_tc else 0,
            "DueDate": self.invoice_date_due or None,
            "DocNo_PO": self.purchase_id.name or None,
        }

        for idx, invoice_line in enumerate(invoice_lines, start=1):
            journal_value_line = journal_value.copy()
            journal_value_line.update({
                "BuiltinOrder": idx or None,
                "DebitAccount": invoice_line.account_id.code or None,
                "CreditAccount": payable_account_code or None,
                "DebitAccount3": tax_line.account_id.code or None,
                "CreditAccount3": payable_account_code or None,
                "TaxCode": tax_line.tax_line_id.code or None,
                "OriginalAmount": invoice_line.price_subtotal,
                "Amount": invoice_line.price_subtotal * exchange_rate,
                "OriginalAmount3": invoice_line.tax_amount,
                "Amount3": invoice_line.tax_amount * exchange_rate,
                "RowId": invoice_line.id or None,
                "JobCode": invoice_line.occasion_code_id.code or None,
                "DeptCode": invoice_line.analytic_account_id.code or None,
                "DocNo_WO": invoice_line.work_order.code or None,
            })

            if is_reversed:
                reversed_account_values = {
                    "DebitAccount": journal_value_line.get("CreditAccount"),
                    "CreditAccount": journal_value_line.get("DebitAccount"),
                    "DebitAccount3": journal_value_line.get("CreditAccount3"),
                    "CreditAccount3": journal_value_line.get("DebitAccount3"),
                }
                journal_value_line.update(reversed_account_values)

            values.append(journal_value_line)

        return values


class AccountMoveVendorBack(models.Model):
    _inherit = 'account.move'

    def bravo_get_purchase_bill_vendor_back_values(self):
        res = []
        columns = self.bravo_get_purchase_bill_vendor_back_columns()
        for record in self:
            res.extend(record.bravo_get_purchase_bill_vendor_back_value())
        return columns, res

    @api.model
    def bravo_get_purchase_bill_vendor_back_columns(self):
        return [
            "CompanyCode", "Stt", "DocCode", "DocNo", "DocDate", "CurrencyCode", "ExchangeRate", "CustomerCode",
            "CustomerName", "Address", "Description", "JobCode", "AtchDocNo", "TaxRegName", "TaxRegNo",
            "DebitAccount", "CreditAccount", "OriginalAmount", "Amount", "OriginalAmount3", "Amount3", "RowId",
            "DeptCode", "AtchDocDate", "AtchDocFormNo", "AtchDocSerialNo", "TaxCode",
        ]

    def bravo_get_purchase_bill_vendor_back_value(self):
        self.ensure_one()
        values = []
        vendor_back_ids = self.vendor_back_ids
        journal_lines = self.line_ids.filtered(lambda l: l.credit > 0)
        credit_account_code = journal_lines[0].account_id.code if journal_lines else None
        value = {
            "DocCode": "NM",
            "DocNo": self.name or None,
            "DocDate": self.date or None,
            "CurrencyCode": self.currency_id.name or None,
            "ExchangeRate": self.exchange_rate,
            "CustomerCode": self.partner_id.ref or None,
            "CustomerName": self.partner_id.name or None,
            "Address": self.partner_id.contact_address_complete or None,
            "Description": self.invoice_description or None,
        }

        for record in vendor_back_ids:
            line_value = value.copy()
            debit_accounts = record.tax_percent.invoice_repartition_line_ids.filtered(lambda l: bool(l.account_id))
            debit_account_code = debit_accounts[0].account_id.code if debit_accounts else None
            line_value.update({
                "CompanyCode": record.company_id.code or None,
                "Stt": record.id,
                "AtchDocNo": record.invoice_reference or None,
                "TaxRegName": record.vendor or None,
                "TaxRegNo": record.code_tax or None,
                "DebitAccount": debit_account_code,
                "CreditAccount": credit_account_code,
                "OriginalAmount": record.price_subtotal_back,
                "Amount": record.price_subtotal_back,
                "OriginalAmount3": record.tax_back,
                "Amount3": record.tax_back,
                "RowId": record.id,
                "AtchDocDate": record._x_invoice_date or None,
                "TaxCode": record.tax_percent.code or None,
            })
            values.append(line_value)

        return values


class StockPickingPurchaseProduct(models.Model):
    _inherit = 'stock.picking'

    def bravo_get_picking_purchase_values(self):
        res = []
        columns = self.bravo_get_picking_purchase_columns()
        employees = self.env['res.utility'].get_multi_employee_by_list_uid(self.user_id.ids + self.env.user.ids)
        for record in self:
            user_id = str(record.user_id.id) or str(self._uid)
            employee = employees.get(user_id) or {}
            res.extend(record.bravo_get_picking_purchase_value(employee.get('code')))
        return columns, res

    @api.model
    def bravo_get_picking_purchase_columns(self):
        return [
            "CompanyCode", "Stt", "DocCode", "DocNo", "DocDate", "CurrencyCode", "ExchangeRate", "CustomerCode",
            "CustomerName", "Address", "Description", "EmployeeCode", "IsTransfer", "CreditAccount",
            "BuiltinOrder", "ItemCode", "ItemName", "UnitPurCode", "DebitAccount", "Quantity9",
            "ConvertRate9", "Quantity", "OriginalPriceUnit",
            "PriceUnit", "OriginalDiscount", "Discount", "OriginalUnitCost", "UnitCost", "OriginalAmount", "Amount",
            "IsPromotions", "DocNo_PO", "WarehouseCode", "JobCode", "RowId", "DocNo_WO", "DeptCode",
        ]

    def bravo_get_picking_purchase_value(self, employee_code):
        count = 1
        values = []
        for stock_move in self.move_ids:
            account_move = stock_move.account_move_ids and stock_move.account_move_ids[0]
            values.append(self.bravo_get_picking_purchase_by_account_move_value(stock_move, account_move, count, employee_code))
            count += 1
        return values

    def bravo_get_picking_purchase_by_account_move_value(self, stock_move, account_move, line_count, employee_code):
        product = stock_move.product_id
        AccountAccount = self.env['account.account']
        if not account_move:
            product_accounts = product.product_tmpl_id.get_product_accounts()
            debit_account = product_accounts.get('stock_valuation') or AccountAccount
            credit_account = product_accounts.get('stock_input') or AccountAccount
        else:
            move_lines = account_move.line_ids
            debit_lines = move_lines.filtered(lambda l: l.debit > 0)
            debit_account = (debit_lines and debit_lines[0]).account_id
            credit_lines = move_lines - debit_lines
            credit_account = (credit_lines and credit_lines[0]).account_id

        purchase_order_line = stock_move.purchase_line_id
        purchase_order = purchase_order_line.order_id
        picking = stock_move.picking_id
        partner = picking.partner_id
        is_partner_group_1 = partner.group_id == \
                             self.env.ref('forlife_pos_app_member.partner_group_1', raise_if_not_found=False)

        # purchase order line info
        exchange_rate = purchase_order.exchange_rate
        vendor_price = purchase_order_line.vendor_price
        original_discount = purchase_order_line.discount / purchase_order_line.purchase_quantity if purchase_order_line.purchase_quantity else 0

        journal_value = {
            "CompanyCode": picking.company_id.code or None,
            "Stt": picking.name or None,
            "DocCode": "NK" if is_partner_group_1 else "NM",
            "DocNo": picking.name or None,
            "DocDate": picking.date_done or None,
            "CurrencyCode": purchase_order.currency_id.name or None,
            "ExchangeRate": exchange_rate or None,
            "CustomerCode": partner.ref or None,
            "CustomerName": partner.name or None,
            "Address": partner.contact_address_complete or None,
            "Description": picking.note or "nhập mua hàng hóa/nguyên vật liệu",
            "EmployeeCode": employee_code or None,
            "IsTransfer": 1 if account_move.is_tc else 0,
            "CreditAccount": credit_account.code or None,
            "BuiltinOrder": line_count or None,
            "ItemCode": product.barcode or None,
            "ItemName": product.name or None,
            "UnitPurCode": purchase_order_line.purchase_uom.code or None,
            "DebitAccount": debit_account.code or None,
            "Quantity9": stock_move.quantity_purchase_done,
            "ConvertRate9": stock_move.quantity_change,
            "Quantity": stock_move.quantity_done,
            "OriginalPriceUnit": vendor_price,
            "PriceUnit": vendor_price * exchange_rate,
            "OriginalDiscount": original_discount,
            "Discount": original_discount * exchange_rate,
            "OriginalUnitCost": vendor_price - original_discount,
            "UnitCost": (vendor_price - original_discount) * exchange_rate or None,
            "OriginalAmount": stock_move.quantity_purchase_done * (vendor_price - original_discount),
            "Amount": (stock_move.quantity_purchase_done * (vendor_price - original_discount)) * exchange_rate,
            "IsPromotions": 1 if stock_move.free_good else 0,
            "DocNo_PO": picking.origin or None,
            "WarehouseCode": stock_move.location_dest_id.warehouse_id.code or None,
            "JobCode": stock_move.occasion_code_id.code or None,
            "RowId": stock_move.id or None,
            "DocNo_WO": stock_move.work_production.code or None,
            "DeptCode": stock_move.account_analytic_id.code or None,
        }

        return journal_value


class AccountMovePurchaseCostingAllocation(models.Model):
    _inherit = 'account.move'

    def bravo_get_picking_purchase_costing_values(self, is_reversed=False):
        res = []
        columns = self.bravo_get_picking_purchase_costing_columns()
        employee = self.env['res.utility'].get_employee_by_uid(self._uid)
        for record in self:
            res.extend(record.bravo_get_picking_purchase_costing_value(is_reversed, employee.get('code')))
        return columns, res

    @api.model
    def bravo_get_picking_purchase_costing_columns(self):
        return [
            "CompanyCode", "Stt", "DocCode", "DocNo", "DocDate", "CurrencyCode", "ExchangeRate", "CustomerCode",
            "CustomerName", "Address", "Description", "EmployeeCode", "IsTransfer", "CreditAccount",
            "BuiltinOrder", "ItemCode", "ItemName", "DebitAccount", "OriginalAmount", "Amount", "DocNo_PO",
            "WarehouseCode", "JobCode", "RowId", "DeptCode",
        ]

    def bravo_get_picking_purchase_costing_value(self, is_reversed, employee_code):
        self.ensure_one()
        picking = self.env['stock.picking'].search([('name', '=', self.ref)], limit=1)
        if not picking:
            return []
        values = []
        lines = self.line_ids

        partner = picking.partner_id
        purchase = self.env['purchase.order'].sudo().search([('name', '=', self.reference)], limit=1)
        journal_value = {
            "CompanyCode": self.company_id.code or None,
            "Stt": self.name or None,
            "DocCode": "XT" if is_reversed else "CP",
            "DocNo": self.name or None,
            "DocDate": self.date or None,
            "CurrencyCode": self.currency_id.name or None,
            "ExchangeRate": self.exchange_rate or None,
            "CustomerCode": partner.ref or None,
            "CustomerName": partner.name or None,
            "Address": partner.contact_address_complete or None,
            "Description": picking.note or "Phân bổ chi phí mua hàng hóa/nguyên vật liệu",
            "EmployeeCode": employee_code or None,
            "IsTransfer": 1 if purchase.has_contract_commerce else 0,
        }
        if not is_reversed:
            credit_lines = lines.filtered(lambda l: l.credit > 0)
            debit_lines = lines - credit_lines
            credit_account_code = credit_lines[0].account_id.code if credit_lines else None
            for idx, line in enumerate(debit_lines, start=1):
                line_value = journal_value.copy()
                line_value.update({
                    "BuiltinOrder": idx or None,
                    "ItemCode": line.product_id.barcode or None,
                    "ItemName": line.product_id.name or None,
                    "DebitAccount": line.account_id.code or None,
                    "OriginalAmount": line.debit,
                    "Amount": line.debit,
                    "DocNo_PO": self.reference or None,
                    "WarehouseCode": picking.location_dest_id.warehouse_id.code or None,
                    "JobCode": line.occasion_code_id.code or None,
                    "RowId": line.id or None,
                    "DeptCode": line.analytic_account_id.code or None,
                    "CreditAccount": credit_account_code or None,
                })
                values.append(line_value)
        else:
            debit_lines = lines.filtered(lambda l: l.debit > 0)
            credit_lines = lines - debit_lines
            debit_account_code = debit_lines[0].account_id.code if debit_lines else None
            for idx, line in enumerate(credit_lines, start=1):
                line_value = journal_value.copy()
                line_value.update({
                    "BuiltinOrder": idx or None,
                    "ItemCode": line.product_id.barcode or None,
                    "ItemName": line.product_id.name or None,
                    "DebitAccount": line.account_id.code or None,
                    "OriginalAmount": line.credit,
                    "Amount": line.credit,
                    "DocNo_PO": self.reference or None,
                    "WarehouseCode": picking.location_dest_id.warehouse_id.code or None,
                    "JobCode": line.occasion_code_id.code or None,
                    "RowId": line.id or None,
                    "DeptCode": line.analytic_account_id.code or None,
                    "CreditAccount": debit_account_code or None,
                })
                values.append(line_value)

        return values


class StockPickingPurchaseReturn(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def bravo_get_return_picking_purchase_columns(self):
        return [
            "CompanyCode", "Stt", "DocCode", "DocNo", "DocDate", "CurrencyCode", "ExchangeRate", "CustomerCode",
            "CustomerName", "Address", "Description", "EmployeeCode", "IsTransfer", "BuiltinOrder", "ItemCode",
            "ItemName", "UnitPurCode", "CreditAccount", "DebitAccount", "Quantity9", "ConvertRate9", "Quantity",
            "OriginalPriceUnit", "PriceUnit", "OriginalDiscount", "Discount", "OriginalUnitCost", "UnitCost",
            "OriginalAmount", "Amount", "IsPromotions", "DocNo_PO", "WarehouseCode", "JobCode",
            "RowId", "DocNo_WO", "RowId_Purchase", "DeptCode",
        ]

    def bravo_get_return_picking_purchase_values(self):
        values = []
        columns = self.bravo_get_return_picking_purchase_columns()
        employee = self.env['res.utility'].get_employee_by_uid(self._uid)
        for record in self:
            for idx, stock_move in enumerate(record.move_ids, start=1):
                values.append(record.bravo_get_return_picking_purchase_value(stock_move, idx, employee.get('code')))
        return columns, values

    def bravo_get_return_picking_purchase_value(self, stock_move, idx, employee_code):
        account_move = stock_move.account_move_ids and stock_move.account_move_ids[0]
        purchase_order_line = stock_move.purchase_line_id
        purchase_order = purchase_order_line.order_id
        exchange_rate = purchase_order.exchange_rate
        picking = stock_move.picking_id
        partner = picking.partner_id
        product = stock_move.product_id
        debit_line = account_move.line_ids.filtered(lambda l: l.debit > 0)
        credit_line = account_move.line_ids.filtered(lambda l: l.credit > 0)
        debit_account = debit_line[0].account_id.code if debit_line else product.categ_id.property_stock_account_input_categ_id.code
        credit_account = credit_line[0].account_id.code if credit_line else product.categ_id.property_stock_valuation_account_id.code
        discount = purchase_order_line.discount / purchase_order_line.purchase_quantity if purchase_order_line.purchase_quantity else 0
        vendor_price = purchase_order_line.vendor_price
        credit = credit_line.credit or 0
        qty_purchase_done = stock_move.quantity_purchase_done or 0
        value = {
            "CompanyCode": picking.company_id.code or None,
            "Stt": picking.name or None,
            "DocCode": "XT",
            "DocDate": picking.date_done or None,
            "CurrencyCode": picking.company_id.currency_id.name or None,
            "ExchangeRate": exchange_rate or None,
            "CustomerCode": partner.ref or None,
            "CustomerName": partner.name or None,
            "Address": partner.contact_address_complete or None,
            "Description": picking.note or "Xuất trả hàng hóa/nguyên vật liệu" or None,
            "EmployeeCode": employee_code or None,
            "IsTransfer": (purchase_order.has_contract_commerce and 1) or 0,
            "BuiltinOrder": idx or None,
            "ItemCode": product.barcode or None,
            "ItemName": product.name or None,
            "UnitPurCode": purchase_order_line.purchase_uom.code or None,
            "CreditAccount": credit_account or None,
            "DebitAccount": debit_account or None,
            "Quantity9": qty_purchase_done,
            "ConvertRate9": stock_move.quantity_change or 0,
            "Quantity": stock_move.quantity_done or 0,
            "OriginalPriceUnit": credit / qty_purchase_done if qty_purchase_done != 0 else 0,
            "PriceUnit": (credit / qty_purchase_done if qty_purchase_done != 0 else 0) * exchange_rate,
            "OriginalDiscount": discount,
            "Discount": discount * exchange_rate,
            "OriginalUnitCost": vendor_price - discount,
            "UnitCost": (vendor_price - discount) * exchange_rate,
            "OriginalAmount": credit,
            "Amount": credit * exchange_rate,
            "IsPromotions": stock_move.free_good or False,
            "DocNo_PO": picking.origin or None,
            "WarehouseCode": picking.location_id.warehouse_id.code or None,
            "JobCode": stock_move.occasion_code_id.code or None,
            "RowId": stock_move.id or None,
            "DocNo_WO": stock_move.work_production.code or None,
            "RowId_Purchase": stock_move.origin_returned_move_id.id or None,
            "DeptCode": stock_move.account_analytic_id.code or None,
        }

        return value
