# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import base64
import xlrd


class ImportPartnerCardRank(models.TransientModel):
    _name = 'import.partner.card.rank'
    _description = 'Import partner card rank'

    brand_id = fields.Many2one("res.brand", string="Brand", required=True)
    row_start = fields.Integer('Row start', default=1)
    import_file = fields.Binary(attachment=False, string='Upload file')
    import_file_name = fields.Char()

    def action_import(self):
        self.ensure_one()
        if not self.import_file:
            raise ValidationError(_("Please upload file template before click Import button !"))
        workbook = xlrd.open_workbook(file_contents=base64.decodebytes(self.import_file))
        partner_cr_exist = []
        partner_cr_by_id = {}
        for cr in self.env['partner.card.rank'].search_read([('brand_id', '=', self.brand_id.id)], ['id', 'customer_id']):
            partner_cr_by_id.update({cr['customer_id'][0]: cr['id']})
            partner_cr_exist.append(cr['customer_id'][0])
        new_data = {}
        add_data = []
        for line in list(self.env['res.utility'].read_xls_book(workbook, 0))[max(0, self.row_start):]:
            customer_id = int(line[0])
            old_card_rank_id = int(line[1])
            new_card_rank_id = int(line[2])
            program_cr_id = int(line[3])
            value_to_upper = int(line[4])
            value_up_rank = int(line[5])
            order_date = line[6]
            if customer_id in partner_cr_exist:
                val = {
                    'partner_card_rank_id': partner_cr_by_id[customer_id],
                    'order_date': order_date,
                    'real_date': order_date,
                    'value_to_upper': value_to_upper,
                    'old_card_rank_id': old_card_rank_id,
                    'new_card_rank_id': new_card_rank_id,
                    'value_up_rank': value_up_rank,
                    'program_cr_id': program_cr_id,
                }
                add_data.append(val)
            else:
                val = [(0, 0, {
                    'old_card_rank_id': old_card_rank_id,
                    'new_card_rank_id': new_card_rank_id,
                    'program_cr_id': program_cr_id,
                    'value_to_upper': value_to_upper,
                    'value_up_rank': value_up_rank,
                    'order_date': order_date,
                    'real_date': order_date,
                })]
                new_data.update({customer_id: new_data.get(customer_id, []) + val})
        if new_data:
            final_new_data = [{
                'customer_id': customer,
                'brand_id': self.brand_id.id,
                'line_ids': value,
            }
                for customer, value in new_data.items()]
            self.env['partner.card.rank'].sudo().create(final_new_data)
        if add_data:
            self.env['partner.card.rank.line'].sudo().create(add_data)
        return True
