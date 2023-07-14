# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import base64
import xlrd


class ImportPartnerCardRank(models.TransientModel):
    _name = 'import.partner.card.rank'
    _description = 'Import partner card rank'

    brand_id = fields.Many2one("res.brand", string="Brand")
    row_start = fields.Integer('Row start', default=2)
    import_file = fields.Binary(attachment=False, string='Upload file')
    import_file_name = fields.Char()
    error_file = fields.Binary(attachment=False, string='Error file')
    error_file_name = fields.Char(default='Error.txt')

    def download_template_file(self):
        attachment_id = self.env.ref(f'forlife_customer_card_rank.template_partner_card_rank_import')
        return {
            'type': 'ir.actions.act_url',
            'name': 'Get template',
            'url': f'web/content/?model=ir.attachment&id={attachment_id.id}&filename_field=name&field=datas&download=true&name={attachment_id.name}',
            'target': 'new'
        }

    @api.onchange('import_file')
    def onchange_import_file(self):
        self.error_file = False

    def action_import(self):
        self.ensure_one()
        if not self.import_file or not self.brand_id:
            raise ValidationError(_("Please choose brand and upload file template before click Import button !"))
        workbook = xlrd.open_workbook(file_contents=base64.decodebytes(self.import_file))
        self._cr.execute(f"""
            select (select json_object_agg(rp.phone, rp.id) from res_partner rp
                    join res_partner_group rpg on rp.group_id = rpg.id and rpg.code = 'C' where rp.phone notnull)       as customers,
                   (select json_object_agg(customer_id, id) from partner_card_rank where brand_id = {self.brand_id.id}) as partner_cr_by_id      
        """)
        data = self._cr.dictfetchone()

        customer_by_phone = data.get('customers') or {}
        partner_cr_by_id = data.get('partner_cr_by_id') or {}
        new_data = {}
        add_data = []
        error = []
        for index, line in enumerate(list(self.env['res.utility'].read_xls_book(workbook, 0))[max(0, self.row_start - 1):]):
            customer_phone = line[0] or ''
            customer_id = customer_by_phone.get(customer_phone)
            if not customer_id:
                error.append(f"Dòng {index + self.row_start}, không tìm khách hàng có số điện thoại là '{line[0]}'")
            old_card_rank_id = int(line[1])
            new_card_rank_id = int(line[2])
            program_cr_id = int(line[3])
            value_to_upper = int(line[4])
            value_up_rank = int(line[5])
            order_date = line[6]
            if customer_id and not error:
                if partner_cr_by_id.get(customer_id):
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
        if error:
            return self.return_error_log('\n'.join(error))
        if new_data:
            final_new_data = [{
                'customer_id': customer,
                'brand_id': self.brand_id.id,
                'line_ids': value,
            }
                for customer, value in new_data.items()]
            while len(final_new_data) > 0:
                number_split = min(500, len(final_new_data))
                split_data = final_new_data[:number_split]
                final_new_data = final_new_data[number_split:]
                self.with_delay(description='Import partner card rank (create)').create_partner_card_rank(split_data)
                # self.create_partner_card_rank(split_data)
        while len(add_data) > 0:
            number_split = min(1000, len(add_data))
            split_data = add_data[:number_split]
            add_data = add_data[number_split:]
            self.with_delay(description='Import partner card rank (update)').create_partner_card_rank_line(split_data)
            # self.create_partner_card_rank_line(split_data)
        return True

    def create_partner_card_rank(self, values):
        self.env['partner.card.rank'].sudo().create(values)

    def create_partner_card_rank_line(self, values):
        self.env['partner.card.rank.line'].sudo().create(values)

    def return_error_log(self, error=''):
        self.write({
            'error_file': base64.encodebytes(error.encode()),
            'import_file': False,
        })
        action = self.env.ref('forlife_customer_card_rank.import_partner_card_rank_action').read()[0]
        action['res_id'] = self.id
        return action
