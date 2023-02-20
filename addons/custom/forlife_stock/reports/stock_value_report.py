# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, tools
from datetime import datetime
import pytz
from ..tools import convert_to_utc_datetime


def read_sql_file(file_path):
    fd = tools.file_open(file_path, 'r')
    sqlFile = fd.read()
    fd.close()
    return sqlFile


class StockValueReport(models.TransientModel):
    _name = 'stock.value.report'
    _description = 'Stock Value Report'

    date_from = fields.Date('From Date', required=True)
    date_to = fields.Date('To Date', default=fields.Date.context_today, required=True)
    detail_ids = fields.One2many('stock.value.report.detail', 'report_id', 'Detail')

    # file sql
    def init(self):
        outgoing_value_diff_report = read_sql_file('./forlife_stock/sql_functions/outgoing_value_diff_report.sql')
        outgoing_value_diff_picking_type_report = read_sql_file(
            './forlife_stock/sql_functions/outgoing_value_diff_picking_type_report.sql')
        stock_incoming_outgoing_report = read_sql_file(
            './forlife_stock/sql_functions/stock_incoming_outgoing_report.sql')
        self.env.cr.execute(outgoing_value_diff_report)
        self.env.cr.execute(outgoing_value_diff_picking_type_report)
        self.env.cr.execute(stock_incoming_outgoing_report)

    def action_get_outgoing_value_diff_report(self):
        # must be utc time
        current_tz = pytz.timezone(self.env.context.get('tz'))
        utc_datetime_from = convert_to_utc_datetime(current_tz, str(self.date_from) + " 00:00:00")
        utc_datetime_to = convert_to_utc_datetime(current_tz, str(self.date_to) + " 23:59:59")
        self._cr.execute("""
            DELETE FROM stock_value_report_detail WHERE create_uid = %s and report_id = %s;
            INSERT INTO stock_value_report_detail (
                                        report_id,
                                        currency_id,
                                        product_id,
                                        opening_quantity,
                                        opening_value,
                                        incoming_quantity,
                                        incoming_value,
                                        odoo_outgoing_quantity,
                                        odoo_outgoing_value,
                                        real_outgoing_price_unit,
                                        real_outgoing_value,
                                        create_date,
                                        write_date,
                                        create_uid,
                                        write_uid)
            SELECT %s,
                    %s,
                    product_id,
                    opening_quantity,
                    opening_value,
                    incoming_quantity,
                    incoming_value,
                    odoo_outgoing_quantity,
                    odoo_outgoing_value,
                    real_outgoing_price_unit,
                    real_outgoing_value,
                    %s,
                    %s,
                    %s,
                    %s
            FROM outgoing_value_diff_report(%s, %s, %s)
        """, (self.env.user.id, self.id, self.id, self.env.company.currency_id.id, datetime.utcnow(), datetime.utcnow(),
              self.env.user.id,
              self.env.user.id, utc_datetime_from, utc_datetime_to, self.env.company.id))

    def action_export_outgoing_value_diff_report(self):
        pass

    def action_export_outgoing_value_diff_picking_type_report(self):
        pass

    def action_get_stock_incoming_outgoing_report(self):
        # must be utc time
        current_tz = pytz.timezone(self.env.context.get('tz'))
        utc_datetime_from = convert_to_utc_datetime(current_tz, str(self.date_from) + " 00:00:00")
        utc_datetime_to = convert_to_utc_datetime(current_tz, str(self.date_to) + " 23:59:59")
        self._cr.execute("""
            DELETE FROM stock_value_report_detail WHERE create_uid = %s and report_id = %s;
            INSERT INTO stock_value_report_detail (
                                        report_id,
                                        currency_id,
                                        product_id,
                                        opening_quantity,
                                        opening_value,
                                        incoming_quantity,
                                        incoming_value,
                                        real_outgoing_price_unit,
                                        real_outgoing_value,
                                        closing_quantity,
                                        closing_value,
                                        create_date,
                                        write_date,
                                        create_uid,
                                        write_uid)
            SELECT %s,
                    %s,
                    product_id,
                    opening_quantity,
                    opening_value,
                    incoming_quantity,
                    incoming_value,
                    real_outgoing_price_unit,
                    real_outgoing_value,
                    closing_quantity,
                    closing_value,
                    %s,
                    %s,
                    %s,
                    %s
            FROM stock_incoming_outgoing_report(%s, %s, %s)
        """, (self.env.user.id, self.id, self.id, self.env.company.currency_id.id, datetime.utcnow(), datetime.utcnow(),
              self.env.user.id,
              self.env.user.id, utc_datetime_from, utc_datetime_to, self.env.company.id))

    def action_export_stock_incoming_outgoing_report(self):
        pass


class StockValueReportDetail(models.TransientModel):
    _name = 'stock.value.report.detail'
    _description = 'Stock Value Report Detail'

    report_id = fields.Many2one('stock.value.report', 'Report')
    currency_id = fields.Many2one('res.currency')
    product_id = fields.Many2one('product.product', 'Product')
    product_code = fields.Char('Product Code', related="product_id.default_code")
    opening_quantity = fields.Integer('Opening Quantity')
    opening_value = fields.Monetary('Opening Value')
    incoming_quantity = fields.Integer('Incoming Quantity')
    incoming_value = fields.Monetary('Incoming Value')
    odoo_outgoing_quantity = fields.Integer('Outgoing Quantity')
    odoo_outgoing_value = fields.Monetary('Outgoing Value')
    real_outgoing_price_unit = fields.Monetary('Real Outgoing Price Unit')
    real_outgoing_value = fields.Monetary('Real Outgoing Value')
    closing_quantity = fields.Integer('Closing Quantity')
    closing_value = fields.Monetary('Closing Value')
