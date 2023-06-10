# -*- coding:utf-8 -*-

from odoo import api, fields, models, _


class AccountMovePurchaseAsset(models.Model):
    _inherit = 'account.move'

    def bravo_get_purchase_asset_service_values(self):
        res = []
        columns = self.bravo_get_purchase_asset_service_columns()
        for record in self:
            res.extend(record.bravo_get_purchase_asset_service_value())
        return columns, res

    @api.model
    def bravo_get_purchase_asset_service_columns(self):
        return [
            "CompanyCode", "DocCode", "DocNo", "DocDate", "CurrencyCode", "ExchangeRate", "CustomerCode",
            "CustomerName", "Address", "Description", "AtchDocDate", "AtchDocNo", "TaxRegName", "TaxRegNo",
            "EmployeeCode", "IsTransfer", "DueDate", "IsCompany", "CreditAccount",
            "BuiltinOrder", "ItemCode", "ItemName", "UnitPurCode", "DebitAccount", "Quantity9", "ConvertRate9",
            "Quantity", "PriceUnit", "Discount", "OriginalUnitCost", "UnitCostCode", "OriginalAmount", "Amount",
            "IsPromotions", "DocNo_PO", "DeptCode", "DocNo_WO", "RowId",
            "TaxCode", "OriginalAmount3", "Amount3", "DebitAccount3", "CreditAccount3"
        ]

    def bravo_get_purchase_asset_service_value(self):
        self.ensure_one()
        values = []
        journal_lines = self.line_ids
        invoice_lines = self.invoice_line_ids
        partner = self.partner_id
        is_partner_group_1 = partner.group_id == \
                             self.env.ref('forlife_pos_app_member.partner_group_1', raise_if_not_found=False)
        # the move has only one vendor -> all invoice lines will have the same partner -> same payable account
        payable_lines = journal_lines.filtered(lambda l: l.account_id.account_type == 'liability_payable')
        journal_lines = journal_lines - payable_lines - invoice_lines
        payable_line = payable_lines and payable_lines[0]
        payable_account_code = payable_line.account_id.code
        exchange_rate = self.exchange_rate

        journal_value = {
            "CompanyCode": self.company_id.code,
            "DocCode": "NK" if is_partner_group_1 else "NM",
            "DocNo": self.name,
            "DocDate": self.date,
            "CurrencyCode": self.currency_id.name,
            "ExchangeRate": exchange_rate,
            "CustomerCode": partner.ref,
            "CustomerName": partner.name,
            "Address": partner.contact_address_complete,
            "Description": self.invoice_description,
            "AtchDocDate": self.date,
            "AtchDocNo": self.number_bills,
            "TaxRegName": partner.name,
            "TaxRegNo": partner.vat,
            "EmployeeCode": self.env.user.employee_id.code,
            "IsTransfer": 1 if self.x_asset_fin else 0,
            "DueDate": self.invoice_date_due,
            "IsCompany": (self.x_root == "Intel" and 1) or (self.x_root == "Winning" and 2) or 0,
            "CreditAccount": payable_account_code,
        }

        for idx, invoice_line in enumerate(invoice_lines, start=1):
            purchase_order = invoice_line.purchase_order_id
            if not purchase_order:
                continue
            product = invoice_line.product_id
            journal_value_line = journal_value.copy()
            journal_value_line.update({
                "BuiltinOrder": idx,
                "ItemCode": product.barcode,
                "ItemName": product.name,
                "UnitPurCode": invoice_line.product_uom_id.code,
                "DebitAccount": invoice_line.account_id.code,
                "Quantity9": invoice_line.quantity_purchased,
                "ConvertRate9": invoice_line.exchange_quantity,
                "Quantity": invoice_line.quantity,
                "PriceUnit": invoice_line.vendor_price,
                "Discount": invoice_line.discount,
                "OriginalUnitCost": invoice_line.vendor_price - invoice_line.discount,
                "UnitCostCode": (invoice_line.vendor_price - invoice_line.discount) * exchange_rate,
                "OriginalAmount": invoice_line.price_subtotal,
                "Amount": invoice_line.price_subtotal * exchange_rate,
                "IsPromotions": invoice_line.promotions,
                "DocNo_PO": purchase_order.name,
                "DeptCode": invoice_line.analytic_account_id.code,
                "DocNo_WO": invoice_line.work_order.code,
                "RowId": invoice_line.id
            })
            invoice_tax_ids = invoice_line.tax_ids
            # get journal line that matched tax with invoice line
            journal_tax_lines = journal_lines.filtered(lambda l: l.tax_line_id & invoice_tax_ids)
            if journal_tax_lines:
                tax_line = journal_tax_lines[0]
                journal_value_line.update({
                    "TaxCode": tax_line.tax_line_id.code,
                    "OriginalAmount3": tax_line.tax_amount,
                    "Amount3": tax_line.tax_amount * exchange_rate,
                    "DebitAccount3": tax_line.account_id.code,
                    "CreditAccount3": payable_account_code
                })

            values.append(journal_value_line)

        return values


class AccountMovePurchaseProduct(models.Model):
    _inherit = 'account.move'

    def bravo_get_purchase_product_values(self):
        res = []
        columns = self.bravo_get_purchase_product_columns()
        for record in self:
            res.extend(record.bravo_get_purchase_product_value())
        return columns, res

    @api.model
    def bravo_get_purchase_product_columns(self):
        return [
            "CompanyCode", "Stt", "DocCode", "DocNo", "DocDate", "CurrencyCode", "ExchangeRate", "CustomerCode",
            "CustomerName", "Address", "Description", "EmployeeCode", "IsTransfer", "DueDate", "BuiltinOrder",
            "DebitAccount", "CreditAccount", "DebitAccount3", "CreditAccount3", "TaxCode", "OriginalAmount",
            "Amount", "OriginalAmount3", "Amount3", "JobCode", "RowId", "DeptCode", "DocNo_WO",
        ]

    def bravo_get_purchase_product_value(self):
        self.ensure_one()
        values = []
        journal_lines = self.line_ids
        invoice_lines = self.invoice_line_ids
        partner = self.partner_id
        # the move has only one vendor -> all invoice lines will have the same partner -> same payable account
        payable_lines = journal_lines.filtered(lambda l: l.account_id.account_type == 'liability_payable')
        journal_lines = journal_lines - payable_lines - invoice_lines
        payable_line = payable_lines and payable_lines[0]
        payable_account_code = payable_line.account_id.code
        exchange_rate = self.exchange_rate

        journal_value = {
            "CompanyCode": self.company_id.code,
            "Stt": self.name,
            "DocCode": "BT",
            "DocNo": self.name,
            "DocDate": self.date,
            "CurrencyCode": self.currency_id.name,
            "ExchangeRate": exchange_rate,
            "CustomerCode": partner.ref,
            "CustomerName": partner.name,
            "Address": partner.contact_address_complete,
            "Description": self.invoice_description,
            "EmployeeCode": self.env.user.employee_id.code,
            "IsTransfer": 1 if self.x_asset_fin == 'TC' else 0,
            "DueDate": self.invoice_date_due,
        }

        for idx, invoice_line in enumerate(invoice_lines, start=1):
            purchase_order = invoice_line.purchase_order_id
            if not purchase_order:
                continue
            journal_value_line = journal_value.copy()
            journal_value_line.update({
                "BuiltinOrder": idx,
                "DebitAccount": invoice_line.account_id.code,
                "CreditAccount": payable_account_code,
                "OriginalAmount": invoice_line.price_subtotal,
                "Amount": invoice_line.price_subtotal * exchange_rate,
                "RowId": invoice_line.id,
                "JobCode": invoice_line.occasion_code_id.code,
                "DeptCode": invoice_line.analytic_account_id.code,
                "DocNo_WO": invoice_line.work_order.code
            })
            invoice_tax_ids = invoice_line.tax_ids
            # get journal line that matched tax with invoice line
            journal_tax_lines = journal_lines.filtered(lambda l: l.tax_line_id and invoice_tax_ids)
            if journal_tax_lines:
                tax_line = journal_tax_lines[0]
                journal_value.update({
                    "DebitAccount3": tax_line.account_id.code,
                    "CreditAccount3": payable_account_code,
                    "TaxCode": tax_line.tax_line_id.code,
                    "OriginalAmount3": tax_line.tax_amount,
                    "Amount3": tax_line.tax_amount * exchange_rate,
                })

            values.append(journal_value)

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
            "CustomerName", "Address", "Description", "AtchDocNo", "TaxRegName", "TaxRegNo", "DebitAccount",
            "CreditAccount", "OriginalAmount", "Amount", "OriginalAmount3", "Amount3", "RowId",
        ]

    def bravo_get_purchase_bill_vendor_back_value(self):
        self.ensure_one()
        values = []
        vendor_back_ids = self.vendor_back_ids
        value = {
            "DocCode": "NM",
            "DocNo": self.name,
            "DocDate": self.date,
            "CurrencyCode": self.currency_id.name,
            "ExchangeRate": self.exchange_rate,
            "CustomerCode": self.partner_id.ref,
            "CustomerName": self.partner_id.name,
            "Address": self.partner_id.contact_address_complete,
            "Description": self.invoice_description
        }

        for record in vendor_back_ids:
            line_value = value.copy()
            line_value.update({
                "CompanyCode": record.company_id.code,
                "Stt": record.id,
                "AtchDocNo": record.invoice_reference,
                "TaxRegName": record.vendor,
                "TaxRegNo": record.code_tax,
                "DebitAccount": False,
                "CreditAccount": False,
                "OriginalAmount": record.price_subtotal_back,
                "Amount": record.price_subtotal_back,
                "OriginalAmount3": record.tax_back,
                "Amount3": record.tax_back,
                "RowId": record.id
            })
            values.append(line_value)

        return values


class StockPickingPurchaseProduct(models.Model):
    _inherit = 'stock.picking'

    def bravo_get_picking_purchase_values(self):
        res = []
        columns = self.bravo_get_picking_purchase_columns()
        for record in self:
            res.extend(record.bravo_get_picking_purchase_value())
        return columns, res

    @api.model
    def bravo_get_picking_purchase_columns(self):
        return [
            "CompanyCode", "Stt", "DocCode", "DocNo", "DocDate", "CurrencyCode", "ExchangeRate", "CustomerCode",
            "CustomerName", "Address", "Description", "EmployeeCode", "IsTransfer", "CreditAccount",
            "BuiltinOrder", "ItemCode", "ItemName", "UnitPurCode", "DebitAccount", "Quantity", "OriginalPriceUnit",
            "PriceUnit", "OriginalDiscount", "Discount", "OriginalUnitCost", "UnitCost", "DocNo_PO", "WarehouseCode",
            "JobCode", "RowId", "DocNo_WO", "DeptCode",
        ]

    def bravo_get_picking_purchase_value(self):
        count = 1
        values = []
        for stock_move in self.move_ids:
            for account_move in stock_move.account_move_ids:
                values.append(self.bravo_get_picking_purchase_by_account_move_value(account_move, count))
                count += 1
        return values

    def bravo_get_picking_purchase_by_account_move_value(self, account_move, line_count):
        stock_move = account_move.stock_move_id
        purchase_order_line = stock_move.purchase_line_id
        product = stock_move.product_id
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
            "CompanyCode": picking.company_id.code,
            "Stt": picking.name,
            "DocCode": "NK" if is_partner_group_1 else "NM",
            "DocNo": picking.name,
            "DocDate": picking.date_done,
            "CurrencyCode": purchase_order.currency_id.name,
            "ExchangeRate": exchange_rate,
            "CustomerCode": partner.ref,
            "CustomerName": partner.name,
            "Address": partner.contact_address_complete,
            "Description": picking.note or "nhập mua hàng hóa/nguyên vật liệu",
            "EmployeeCode": self.env.user.employee_id.code,
            "IsTransfer": (purchase_order.has_contract_commerce and 1) or 0,
            "CreditAccount": ...,
            "BuiltinOrder": line_count,
            "ItemCode": product.barcode,
            "ItemName": product.name,
            "UnitPurCode": purchase_order_line.purchase_uom.code,
            "DebitAccount": ...,
            "Quantity": stock_move.quantity_done,
            "OriginalPriceUnit": vendor_price,
            "PriceUnit": vendor_price * exchange_rate,
            "OriginalDiscount": original_discount,
            "Discount": original_discount * exchange_rate,
            "OriginalUnitCost": vendor_price - original_discount,
            "UnitCost": (vendor_price - original_discount) * exchange_rate,
            "DocNo_PO": picking.origin,
            "WarehouseCode": stock_move.location_dest_id.warehouse_id.code,
            "JobCode": stock_move.occasion_code_id.code,
            "RowId": stock_move.id,
            "DocNo_WO": stock_move.work_production.code,
            "DeptCode": stock_move.account_analytic_id.code
        }

        for move_line in account_move.line_ids:
            if move_line.debit:
                journal_value.update({
                    'DebitAccount': move_line.account_id.code
                })
            else:
                journal_value.update({
                    'CreditAccount': move_line.account_id.code
                })

        return journal_value


class AccountMovePurchaseCostingAllocation(models.Model):
    _inherit = 'account.move'

    def bravo_get_picking_purchase_costing_values(self):
        res = []
        columns = self.bravo_get_picking_purchase_costing_columns()
        for record in self:
            res.extend(record.bravo_get_picking_purchase_costing_value())
        return columns, res

    @api.model
    def bravo_get_picking_purchase_costing_columns(self):
        return [
            "CompanyCode", "Stt", "DocCode", "DocNo", "DocDate", "CurrencyCode", "ExchangeRate", "CustomerCode",
            "CustomerName", "Address", "Description", "EmployeeCode", "IsTransfer", "CreditAccount",
            "BuiltinOrder", "ItemCode", "ItemName", "DebitAccount", "OriginalAmount", "Amount", "DocNo_PO",
            "WarehouseCode", "JobCode", "RowId", "DeptCode",
        ]

    def bravo_get_picking_purchase_costing_value(self):
        self.ensure_one()
        picking = self.env['stock.picking'].search([('name', '=', self.ref)], limit=1)
        if not picking:
            return []
        values = []
        lines = self.line_ids
        credit_lines = lines.filtered(lambda l: l.credit > 0)
        debit_lines = lines - credit_lines
        credit_account_code = credit_lines[0].account_id.code if credit_lines else None
        partner = picking.partner_id
        purchase = self.env['purchase.order'].sudo().search([('name', '=', self.reference)], limit=1)
        journal_value = {
            "CompanyCode": self.company_id.code,
            "Stt": self.name,
            "DocCode": "CP",
            "DocNo": self.name,
            "DocDate": self.date,
            "CurrencyCode": self.currency_id.name,
            "ExchangeRate": self.exchange_rate,
            "CustomerCode": partner.ref,
            "CustomerName": partner.name,
            "Address": partner.contact_address_complete,
            "Description": self.ref,
            "EmployeeCode": self.env.user.employee_id.code,
            "IsTransfer": 1 if purchase.has_contract_commerce else 0,
            "CreditAccount": credit_account_code,
        }
        for idx, line in enumerate(debit_lines, start=1):
            line_value = journal_value.copy()
            line_value.update({
                "BuiltinOrder": idx,
                "ItemCode": line.product_id.barcode,
                "ItemName": line.product_id.name,
                "DebitAccount": line.account_id.code,
                "OriginalAmount": line.debit,
                "Amount": line.debit,
                "DocNo_PO": self.reference,
                "WarehouseCode": self.ref,
                "JobCode": line.occasion_code_id.code,
                "RowId": line.id,
                "DeptCode": line.analytic_account_id.code
            })

            values.append(line_value)

        return values
