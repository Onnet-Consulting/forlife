import base64

import xlrd

from odoo import fields, models, _
from odoo.exceptions import ValidationError


class PosOrderImport(models.TransientModel):
    _name = 'pos.order.import'
    _description = "Pos order import"

    name = fields.Char(default='Nhập từ excel')
    file = fields.Binary(string='File excel')
    file_name = fields.Char(string='Tên file')
    file_template = fields.Binary(string='Template default', compute='get_default_template')

    # def get_default_template(self):
    #     for rec in self:
    #         path = get_resource_path('forlife_purchase', 'data/xml', 'template_lsx.xlsx')
    #         rec.file_template = base64.b64encode(open(path, "rb").read())
    #
    # def download_template(self):
    #     export = {
    #         'type': 'ir.actions.act_url',
    #         'name': 'Export fee',
    #         'url': '/web/content/%s/%s/file_template/template_lsx.xlsx?download=true' % (self._name, self.id),
    #     }
    #     return export

    def get_product_id(self, barcode):
        query = '''
                            SELECT id FROM product_product WHERE barcode = %(barcode)s LIMIT 1
                        '''
        self.env.cr.execute(query, {'barcode': barcode})
        data = self.env.cr.fetchall()
        return data[0]

    def get_store_id(self, name):
        query = '''
                            SELECT id FROM store WHERE name = %(name)s LIMIT 1
                        '''
        self.env.cr.execute(query, {'name': name})
        data = self.env.cr.fetchall()
        return data[0]

    def get_partner_id(self, phone):
        query = '''
                            SELECT id FROM res_partner WHERE phone = %(phone)s LIMIT 1
                        '''
        self.env.cr.execute(query, {'phone': phone})
        data = self.env.cr.fetchall()
        return data[0]

    def get_pos_config_id(self, store_id):
        query = '''
                            SELECT id FROM pos_config WHERE store_id = %(store_id)s LIMIT 1
                        '''
        self.env.cr.execute(query, {'store_id': store_id})
        data = self.env.cr.fetchall()
        return data[0]

    def get_pos_session_id(self, config_id):
        query = '''
                            SELECT id FROM pos_session WHERE config_id = %(config_id)s AND name = %(name)s LIMIT 1
                        '''
        self.env.cr.execute(query, {'config_id': config_id, 'name': 'old-session-' + str(config_id)})
        data = self.env.cr.fetchall()
        return data[0] if data else False

    def create_pos_session(self, config_id):
        query = '''
                    INSERT INTO pos_session(config_id, user_id, name, state, start_at, stop_at, company_id)
                    VALUES(%(config_id)s, 2, %(name)s, 'closed', '2023-10-02 00:00:00', '2023-10-02 10:00:00', 5)
                    RETURNING id
                '''
        self.env.cr.execute(query, {'config_id': config_id, 'name': 'old-session-' + str(config_id)})
        data = self.env.cr.fetchall()
        return data[0]

    def create_pos_order(self, data):

        query = '''
                    INSERT INTO pos_order(date_order, store_id, pos_reference, session_id, partner_id, company_id, pricelist_id, name,
                                          amount_tax, amount_total, amount_paid, amount_return, issue_invoice_type, brand_id)
                    VALUES(%(date_order)s, %(store_id)s, %(pos_reference)s, %(session_id)s, %(partner_id)s, %(company_id)s, 2, %(pos_reference)s, 0, %(amount_total)s, %(amount_paid)s, 0, 'vat', %(brand_id)s)
                    RETURNING id
                '''
        self.env.cr.execute(query, data)
        data = self.env.cr.fetchall()
        return data[0]

    def create_pos_order_line(self, data):

        query = '''
                    INSERT INTO pos_order_line (order_id, product_id, qty, original_price, price_unit, price_subtotal, price_subtotal_incl, name, employee_id)
                    VALUES (%(order_id)s, %(product_id)s, %(qty)s, %(original_price)s, %(price_unit)s, %(price_subtotal)s, %(price_subtotal_incl)s, %(name)s, %(employee_id)s) RETURNING id;
                '''
        self.env.cr.execute(query, data)
        data = self.env.cr.fetchall()
        return data[0]

    def create_pos_order_line_discount(self, data):

        query = '''
                    INSERT INTO pos_order_line_discount_details (pos_order_line_id, money_reduced) VALUES (%(pos_order_line_id)s, %(money_reduced)s) RETURNING id;
                '''
        self.env.cr.execute(query, data)
        data = self.env.cr.fetchall()
        return data[0]

    def apply(self):
        wb = xlrd.open_workbook(file_contents=base64.decodebytes(self.file))
        data = list(self.env['res.utility'].read_xls_book(book=wb, sheet_index=0))
        header = data[0]
        draw_orders = data[1:]
        orders = {}
        mess = ''
        for draw_order in draw_orders:
            if orders.get(draw_order[2], False):
                orders[draw_order[2]]['amount_paid'] += draw_order[8]
                orders[draw_order[2]]['amount_total'] += draw_order[8]
                orders[draw_order[2]]['lines'].append({
                    'product_id': self.get_product_id(draw_order[4]),
                    'qty': draw_order[5],
                    'original_price': draw_order[6],
                    'money_is_reduced': draw_order[7],
                    'subtotal_paid': draw_order[8],
                    'employee_id': draw_order[9],
                    'name': draw_order[10]
                })
            else:
                orders[draw_order[2]] = {
                    'date_order': draw_order[0],
                    'store_id': self.get_store_id(draw_order[1]),
                    'pos_reference': draw_order[2],
                    'partner_id': self.get_partner_id(draw_order[3]),
                    'amount_paid': draw_order[8],
                    'amount_total': draw_order[8],
                    'brand_id': draw_order[11],
                    'company_id': draw_order[12],
                    'lines': [{
                        'product_id': self.get_product_id(draw_order[4]),
                        'qty': draw_order[5],
                        'original_price': draw_order[6],
                        'money_is_reduced': draw_order[7],
                        'subtotal_paid': draw_order[8],
                        'employee_id': draw_order[9],
                        'name': draw_order[10]
                    }]
                }

        for order_key in orders:
            try:
                order = orders.get(order_key)
                config_id = self.get_pos_config_id(order['store_id'])
                session_id = self.get_pos_session_id(config_id)
                if not session_id:
                    session_id = self.create_pos_session(config_id)
                data_order = {'date_order': order['date_order'], 'store_id': order['store_id'],
                              'pos_reference': order['pos_reference'],
                              'session_id': session_id, 'partner_id': order['partner_id'],
                              'amount_paid': order['amount_paid'], 'amount_total': order['amount_total'],
                              'brand_id': order['brand_id'], 'company_id': order['company_id']}
                pos_order_id = self.create_pos_order(data_order)
                for line in order['lines']:
                    data_order_line = {
                        'order_id': pos_order_id,
                        'product_id': line['product_id'],
                        'qty': line['qty'],
                        'original_price': line['original_price'],
                        'price_unit': line['original_price'],
                        'price_subtotal': line['subtotal_paid'],
                        'price_subtotal_incl': line['subtotal_paid'],
                        'name': line['name'],
                        'employee_id': line['employee_id']
                    }
                    pos_order_line_id = self.create_pos_order_line(data_order_line)
                    pos_order_line_discount_data = {
                        'pos_order_line_id': pos_order_line_id,
                        'money_reduced': line['money_is_reduced'],
                    }
                    pos_order_line_discount_id = self.create_pos_order_line_discount(pos_order_line_discount_data)
            except Exception as ex:
                mess += '\n '+order_key+' :\n'+ex

            if mess:
                raise ValidationError(mess)

        return

    def _check_exist_production(self, code):
        productions = self.env['forlife.production'].search([('code', '=', code), ('active', '=', True)])
        result = False
        for production in productions:
            for line in production.forlife_production_finished_product_ids:
                if line.stock_qty != 0:
                    result = True
        return result
