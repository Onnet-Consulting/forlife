import base64
import xlrd
from odoo import fields, api, models
from datetime import datetime


class ImportProductionFromExcel(models.TransientModel):
    _name = 'import.production.from.excel'

    name = fields.Char(default='Nhập từ excel')
    file = fields.Binary(string='File excel')
    file_name = fields.Char(string='Tên file')

    def apply(self):
        wb = xlrd.open_workbook(file_contents=base64.decodebytes(self.file))
        orders = list(self.env['res.utility'].read_xls_book(book=wb, sheet_index=0))[1:]
        material = list(self.env['res.utility'].read_xls_book(book=wb, sheet_index=1))[1:]
        list_account = []
        list_product = []
        uom = []
        list_production = []
        for o in orders:
            list_account += [o[4], [o[5]]]
            list_product += [o[9]]
            if o[0]:
                list_production += [o[0]]
        for m in material:
            list_product.append(m[0])
            uom.append(m[4])

        account_aa = self.env['account.analytic.account'].search_read([
            ('company_id', '=', self.env.company.id),
            ('code', 'in', list_account),
        ], ['id', 'code'])
        product = self.env['product.product'].search_read([
            ('barcode', 'in', list_product),
        ], ['id', 'barcode'])
        uom_uom = self.env['uom.uom'].search_read([
            ('name', 'in', uom),
        ], ['id', 'name'])
        production_exists = self.env['forlife.production'].search_read([
            ('code', 'in', list_production),
        ], ['version', 'code'])

        department = {}
        product_dict = {}
        uom_dict = {}
        production_exists_dict = {}
        for a in account_aa:
            department.update({a['code']: a['id']})
        for p in product:
            product_dict.update({p['barcode']: p['id']})
        for u in uom_uom:
            uom_dict.update({u['name']: u['id']})
        for pe in production_exists:
            production_exists_dict.update({pe['code']: pe['version']})

        num = 0
        create_list_order = []
        for order in orders:
            master = {}
            if not production_exists_dict.get(order[0], False):
                production_exists_dict[order[0]] = 1
            else:
                production_exists_dict[order[0]] += 1
            if order[0]:
                master = {
                    'code': order[0],
                    'version': production_exists_dict.get(order[0], 1),
                    'name': order[1],
                    'user_id': order[2] or self.env.user.id,
                    'created_date': order[3] or datetime.today(),
                    'implementation_id': department.get(order[4], False),
                    'management_id': department.get(order[5], False),
                    'production_department': order[6],
                    'produced_from_date': order[7],
                    'to_date': order[8],
                }
            if order[9]:
                child_value = {
                    'product_id': product_dict.get(order[9], False),
                    'produce_qty': int(order[12]),
                }

                list_material = []
                for m in material:
                    if m[1] == order[10] or m[2] == order[11] or (not m[1] and not m[2]):
                        if not product_dict.get(m[0], False):
                            continue
                        if not uom_dict.get(m[4], False):
                            continue
                        list_material.append((0, 0, {
                            'product_id': product_dict.get(m[0], False),
                            'production_uom_id': uom_dict.get(m[4], False),
                            'conversion_coefficient': m[5],
                            'rated_level': m[6],
                            'loss': m[7],
                        }))
                child_value['forlife_bom_material_ids'] = list_material
                child = [(0, 0, child_value)]
                if len(create_list_order) >= 1 and not order[0]:
                    create_list_order[len(create_list_order) - 1]['forlife_production_finished_product_ids'] += child
                else:
                    master['forlife_production_finished_product_ids'] = child
            if master:
                create_list_order.append(master)

        production = self.env['forlife.production'].create(create_list_order)
        action = self.env.ref('forlife_purchase.forlife_production_action').read()[0]
        return action