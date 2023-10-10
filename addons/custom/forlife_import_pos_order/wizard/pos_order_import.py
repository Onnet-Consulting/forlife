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
        data = self.env.cr.fetchone()
        if data:
            return data[0]
        else:
            raise ValidationError('Khong co product: '+ barcode)

    def get_promotion_program_id(self, name):
        query = '''
                            SELECT id FROM promotion_program WHERE name = %(name)s LIMIT 1
                        '''
        self.env.cr.execute(query, {'name': name})
        data = self.env.cr.fetchone()
        if data:
            return data[0]
        else:
            raise ValidationError('Khong co chuong trinh KM: ' + name)

    def get_point_program_id(self, name):
        query = '''
                            SELECT id FROM points_promotion WHERE name = %(name)s LIMIT 1
                        '''
        self.env.cr.execute(query, {'name': name})
        data = self.env.cr.fetchone()
        if data:
            return data[0]
        else:
            raise ValidationError('Khong co chuong trinh DIEM: ' + name)

    def get_card_rank_program_id(self, name):
        query = '''
                            SELECT id FROM member_card WHERE name = %(name)s LIMIT 1
                        '''
        self.env.cr.execute(query, {'name': name})
        data = self.env.cr.fetchone()
        if data:
            return data[0]
        else:
            raise ValidationError('Khong co chuong trinh hang the: ' + name)

    def get_store_id(self, name):
        query = '''
                            SELECT id FROM store WHERE name = %(name)s LIMIT 1
                        '''
        self.env.cr.execute(query, {'name': name})
        data = self.env.cr.fetchone()
        if data:
            return data[0]
        else:
            raise ValidationError('Khong co store: ' + name)

    def get_partner_id(self, phone):
        query = '''
                            SELECT id FROM res_partner WHERE phone = %(phone)s LIMIT 1
                        '''
        self.env.cr.execute(query, {'phone': phone})
        data = self.env.cr.fetchone()
        return data[0] if data else 6801233

    def get_pos_config_id(self, store_id):
        query = '''
                            SELECT id FROM pos_config WHERE store_id = %(store_id)s LIMIT 1
                        '''
        self.env.cr.execute(query, {'store_id': store_id})
        data = self.env.cr.fetchone()
        if data:
            return data[0]
        else:
            raise ValidationError('Khong co pos_config: '+store_id)

    def get_pos_session_id(self, config_id):
        query = '''
                            SELECT id FROM pos_session WHERE config_id = %(config_id)s AND name = %(name)s LIMIT 1
                        '''
        self.env.cr.execute(query, {'config_id': config_id, 'name': 'old-session-' + str(config_id)})
        data = self.env.cr.fetchone()
        if data:
            return data[0]
        else:
            return False

    def create_pos_session(self, config_id):
        query = '''
                    INSERT INTO pos_session(config_id, user_id, name, state, start_at, stop_at)
                    VALUES(%(config_id)s, 2, %(name)s, 'closed', '2023-10-02 00:00:00', '2023-10-02 10:00:00')
                    RETURNING id
                '''
        self.env.cr.execute(query, {'config_id': config_id, 'name': 'old-session-' + str(config_id)})
        data = self.env.cr.fetchone()
        return data[0]

    def create_pos_order(self, data):

        query = '''
                    INSERT INTO pos_order(date_order, store_id, pos_reference, session_id, partner_id, company_id, pricelist_id, name,
                                          amount_tax, amount_total, amount_paid, amount_return, issue_invoice_type,
                                           brand_id, point_order, total_point, program_store_point_id, card_rank_program_id)
                    VALUES(%(date_order)s, %(store_id)s, %(pos_reference)s, %(session_id)s, %(partner_id)s,
                     %(company_id)s, 1, %(pos_reference)s, 0, %(amount_total)s, %(amount_paid)s, 0, 'vat', %(brand_id)s,
                      %(point_order)s, %(total_point)s, %(program_store_point_id)s, %(card_rank_program_id)s )
                    RETURNING id
                '''
        self.env.cr.execute(query, data)
        data = self.env.cr.fetchone()
        return data[0]

    def create_pos_order_line(self, data):

        query = '''
INSERT INTO pos_order_line (order_id, product_id, qty, original_price, price_unit, price_subtotal, price_subtotal_incl,
    name, employee_id, is_reward_line, with_purchase_condition, full_product_name)
VALUES (%(order_id)s, %(product_id)s, %(qty)s, %(original_price)s, %(price_unit)s, %(price_subtotal)s,
    %(price_subtotal_incl)s, %(name)s, %(employee_id)s, %(is_reward_line)s, %(with_purchase_condition)s, %(full_product_name)s) RETURNING id;
'''
        self.env.cr.execute(query, data)
        data = self.env.cr.fetchone()
        return data[0]

    def create_pos_order_line_discount(self, data):

        query = '''
INSERT INTO pos_order_line_discount_details (pos_order_line_id, type, money_reduced, recipe, discounted_amount) 
VALUES (%(pos_order_line_id)s, %(type)s , %(money_reduced)s, %(recipe)s, %(discounted_amount)s) RETURNING id;
'''
        self.env.cr.execute(query, data)
        data = self.env.cr.fetchone()
        return data[0]

    def create_promotion_usage_line(self, data):

        query = '''
                    INSERT INTO promotion_usage_line (order_line_id, program_id, discount_amount, registering_tax) 
                    VALUES (%(order_line_id)s, %(program_id)s , %(discount_amount)s, %(registering_tax)s) RETURNING id;
                '''
        self.env.cr.execute(query, data)
        data = self.env.cr.fetchone()
        return data[0]

    def create_account_tax_pos_order_line_rel(self, data):

        query = '''
                    INSERT INTO account_tax_pos_order_line_rel (pos_order_line_id, account_tax_id) VALUES (%(pos_order_line_id)s, %(account_tax_id)s);
                '''
        self.env.cr.execute(query, data)
        return True

    def apply(self):
        wb = xlrd.open_workbook(file_contents=base64.decodebytes(self.file))
        data = list(self.env['res.utility'].read_xls_book(book=wb, sheet_index=0))
        header = data[0]
        draw_orders = data[1:]
        orders = {}
        mess = ''
        for draw_order in draw_orders:
            if orders.get(draw_order[2], False):
                orders[draw_order[2]]['amount_paid'] += int(draw_order[12])
                orders[draw_order[2]]['amount_total'] += int(draw_order[12])
                orders[draw_order[2]]['lines'].append({
                    'full_product_name': draw_order[14],
                    'product_id': draw_order[8],
                    'qty': draw_order[9],
                    'original_price': draw_order[10],
                    'money_is_reduced': draw_order[11],
                    'subtotal_paid': draw_order[12],
                    'employee_id': draw_order[13],
                    'name': draw_order[14],
                    'tax_id': draw_order[17],
                    'is_reward_line': draw_order[18],
                    'with_purchase_condition': draw_order[19],
                    'discount_details_lines': [{
                        'type': draw_order[20],
                        'money_reduced': float(draw_order[21]),
                        'discounted_amount': draw_order[21],
                    }] if draw_order[20] and draw_order[21] else [],
                    'promotion_usage_ids': [{
                        'program_id': draw_order[22],
                        'discount_amount': draw_order[23],
                        'registering_tax': draw_order[24]
                    }] if draw_order[22] and draw_order[23] else [],
                })
            else:
                orders[draw_order[2]] = {
                    'date_order': draw_order[0],
                    'store_id': draw_order[1],
                    'pos_reference': draw_order[2],
                    'partner_id': self.get_partner_id(draw_order[3]),
                    'amount_paid': int(draw_order[12]),
                    'amount_total': int(draw_order[12]),
                    'brand_id': draw_order[15],
                    'company_id': draw_order[16],
                    'program_store_point_id': draw_order[4],
                    'point_order': draw_order[5],
                    'total_point': draw_order[6],
                    'card_rank_program_id': draw_order[7],
                    'lines': [{
                        'full_product_name': draw_order[14],
                        'product_id': draw_order[8],
                        'qty': draw_order[9],
                        'original_price': draw_order[10],
                        'money_is_reduced': draw_order[11],
                        'subtotal_paid': draw_order[12],
                        'employee_id': draw_order[13],
                        'name': draw_order[14],
                        'tax_id': draw_order[17],
                        'is_reward_line': draw_order[18],
                        'with_purchase_condition': draw_order[19],
                        'discount_details_lines': [{
                            'type': draw_order[20],
                            'money_reduced': float(draw_order[21]),
                            'discounted_amount': draw_order[21],
                        }] if draw_order[20] and draw_order[21] else [],
                        'promotion_usage_ids': [{
                            'program_id': draw_order[22],
                            'discount_amount': draw_order[23],
                            'registering_tax': draw_order[24]
                        }] if draw_order[22] and draw_order[23] else [],
                    }]
                }

        for order_key in orders:
            try:
                order = orders.get(order_key)
                store_id = self.get_store_id(order['store_id'])
                config_id = self.get_pos_config_id(store_id)
                session_id = self.get_pos_session_id(config_id)
                if not session_id:
                    session_id = self.create_pos_session(config_id)
                data_order = {'date_order': order['date_order'], 'store_id': store_id,
                              'pos_reference': order['pos_reference'],
                              'session_id': session_id, 'partner_id': order['partner_id'],
                              'amount_paid': order['amount_paid'], 'amount_total': order['amount_total'],
                              'brand_id': order['brand_id'], 'company_id': order['company_id'],
                              'point_order': order['point_order'], 'total_point': order['total_point']}
                program_store_point_id = None
                if order['program_store_point_id']:
                    program_store_point_id = self.get_point_program_id(order['program_store_point_id'])
                data_order['program_store_point_id'] = program_store_point_id

                card_rank_program_id = None
                if order['card_rank_program_id']:
                    card_rank_program_id = self.get_card_rank_program_id(order['card_rank_program_id'])
                data_order['card_rank_program_id'] = card_rank_program_id

                pos_order_id = self.create_pos_order(data_order)
                for line in order['lines']:
                    data_order_line = {
                        'order_id': pos_order_id,
                        'full_product_name': '[' + line['product_id'] + '] ' + line['full_product_name'],
                        'product_id': self.get_product_id(line['product_id']),
                        'qty': line['qty'],
                        'original_price': line['original_price'],
                        'price_unit': line['original_price'],
                        'price_subtotal': int(line['qty']) * int(line['original_price']),
                        'price_subtotal_incl': int(line['qty']) * int(line['original_price']),
                        'name': line['name'],
                        'employee_id': line['employee_id'],
                        'is_reward_line': line['is_reward_line'],
                        'with_purchase_condition': line['with_purchase_condition'],
                    }
                    pos_order_line_id = self.create_pos_order_line(data_order_line)

                    if line['discount_details_lines']:
                        line['discount_details_lines'][0]['pos_order_line_id'] = pos_order_line_id
                        line['discount_details_lines'][0]['recipe'] = line['discount_details_lines'][0]['money_reduced']/ 1000 \
                            if line['discount_details_lines'][0]['type'] == 'point' else line['discount_details_lines'][0]['money_reduced']
                        pos_order_line_discount_data = line['discount_details_lines'][0]
                        pos_order_line_discount_id = self.create_pos_order_line_discount(pos_order_line_discount_data)

                    if line['promotion_usage_ids']:
                        program_id = self.get_promotion_program_id(line['promotion_usage_ids'][0]['program_id'])
                        line['promotion_usage_ids'][0]['program_id'] = program_id
                        line['promotion_usage_ids'][0]['order_line_id'] = pos_order_line_id
                        promotion_usage_line_data = line['promotion_usage_ids'][0]
                        promotion_usage_line_id = self.create_promotion_usage_line(promotion_usage_line_data)

                    create_account_tax_pos_order_line_rel_data = {
                        'pos_order_line_id': pos_order_line_id,
                        'account_tax_id': line['tax_id']
                    }
                    self.create_account_tax_pos_order_line_rel(create_account_tax_pos_order_line_rel_data)
            except Exception as ex:
                raise ex
                mess += '\n '+order_key+' :\n'+ str(ex)

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
