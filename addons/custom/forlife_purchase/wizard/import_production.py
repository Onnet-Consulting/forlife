import base64
import xlrd
from odoo import fields, api, models, _
from datetime import datetime
from odoo.exceptions import ValidationError
from odoo.modules.module import get_resource_path
import itertools


class ImportProductionFromExcel(models.TransientModel):
    _name = 'import.production.from.excel'
    _description = "Production import"

    name = fields.Char(default='Nhập từ excel')
    file = fields.Binary(string='File excel')
    file_name = fields.Char(string='Tên file')
    file_template = fields.Binary(string='Template default', compute='get_default_template')

    def get_default_template(self):
        for rec in self:
            path = get_resource_path('forlife_purchase', 'data/xml', 'template_lsx_v2.xlsx')
            rec.file_template = base64.b64encode(open(path, "rb").read())

    def download_template(self):
        export = {
            'type': 'ir.actions.act_url',
            'name': 'Export fee',
            'url': '/web/content/%s/%s/file_template/template_lsx.xlsx?download=true' % (self._name, self.id),
        }
        self.file_template = False
        return export

    def validate_date(self, date_string):
        try:
            date_string = datetime.strptime(date_string.strip(), '%d/%m/%Y').strftime('%Y-%m-%d')
        except:
            date_string = date_string
        return date_string

    def apply(self):
        wb = xlrd.open_workbook(file_contents=base64.decodebytes(self.file))
        orders = list(self.env['res.utility'].read_xls_book(book=wb, sheet_index=0))[1:]
        material = list(self.env['res.utility'].read_xls_book(book=wb, sheet_index=1))[1:]
        expense = list(self.env['res.utility'].read_xls_book(book=wb, sheet_index=2))[1:]

        list_account = []
        list_product = []
        uom = []
        list_production = []
        list_partners = []
        list_employee = []
        list_brand = []

        for o in orders:
            list_account += [o[2], [o[3]]]
            list_product += [o[11]]
            list_partners += [o[10]]
            list_employee += [o[9]]
            list_brand += [o[8]]

            if o[0]:
                list_production += [o[0]]

        data_material_good = {}
        key_material = ''
        for m in material:
            list_product.append(m[1])
            list_product.append(m[2])
            uom.append(m[6])
            if m[0]:
                key_material = m[0]
                data_material_good[m[0]] = [m[1:]]
            else:
                data_material_good[key_material] += [m[1:]]

        key_expense = ''
        data_expense_good = {}
        for ep in expense:
            list_product.append(ep[1])
            if ep[0]:
                key_expense = ep[0]
                data_expense_good[ep[0]] = [ep[1:]]
            else:
                data_expense_good[key_expense] += [ep[1:]]

        account_aa = self.env['account.analytic.account'].search_read([
            ('company_id', '=', self.env.company.id),
            ('code', 'in', list_account),
        ], ['id', 'code'])
        product = self.env['product.product'].search_read([
            '|', ('barcode', 'in', list_product), ('makithuat', 'in', list_product)
        ], ['id', 'barcode', 'makithuat'])
        uom_uom = self.env['uom.uom'].search_read([
            ('name', 'in', uom),
        ], ['id', 'name'])

        brands = self.env['res.brand'].search_read([
            ('code', 'in', list_brand),
        ], ['id', 'code'])

        partners = self.env['res.partner'].search_read([
            ('ref', 'in', list_partners),
        ], ['id', 'ref'])

        employees = self.env['hr.employee'].search_read([
            ('code', 'in', list_employee),
        ], ['id', 'code'])

        department = {}
        product_dict = {}
        uom_dict = {}
        brand = {}
        partner = {}
        employee = {}
        for a in account_aa:
            department.update({a['code']: a['id']})
        for p in product:
            product_dict.update({p['barcode']: p['id'], p['makithuat']: p['id']})
        for u in uom_uom:
            uom_dict.update({u['name']: u['id']})
        for p in partners:
            partner.update({p['ref']: p['id']})
        for b in brands:
            brand.update({b['code']: b['id']})
        for e in employees:
            employee.update({e['code']: e['id']})

        create_list_order = []
        production_code = ''
        for order in orders:
            check_exist = self._check_exist_production(order[0])
            if check_exist:
                raise ValidationError('Lệnh sản xuất mã %s đã có hành động nhập kho thành phẩm. Vui lòng kiểm tra lại!' %order[0])
            master = {
                'forlife_production_finished_product_ids': [],
                'material_import_ids': [],
                'expense_import_ids': [],
            }
            if order[0]:
                production_code = order[0]
                master = {
                    'code': order[0],
                    'name': order[1],
                    'implementation_id': department.get(order[2].strip(), False),
                    'management_id': department.get(order[3].strip(), False),
                    'production_department': order[4],
                    'produced_from_date': self.validate_date(order[5]),
                    'to_date': self.validate_date(order[6]),
                    'production_price': order[7],
                    'brand_id': brand.get(order[8].strip(), False),
                    'leader_id':  employee.get(order[9].strip(), False),
                    'machining_id': partner.get(order[10].strip(), False),
                }
            if order[11]:
                if not product_dict.get(order[11], False):
                    raise ValidationError(_('Không có Mã thành phẩm với mã %s trong danh mục sản phẩm.' % order[11]))
                child_value = {
                    'product_id': product_dict.get(order[11], False),
                    'produce_qty': int(round(float(order[12]), 0)),
                }

                product = self.env['product.product'].browse(product_dict.get(order[11]))
                attr_value = self.env['res.utility'].get_attribute_code_config()
                sql = f"""
                    select COALESCE(pav.name->>'vi_VN', pav.name->>'en_US') AS name from product_attribute_value pav 
                    join product_attribute pa on pav.attribute_id = pa.id 
                    where pa.attrs_code  in ('{attr_value.get('size')}', '{attr_value.get('mau_sac')}');
                """
                self._cr.execute(sql)
                attributes = self._cr.fetchall()
                attributes = list(itertools.chain(*attributes))
                product_variant = product.mapped('attribute_line_ids.value_ids.name')
                list_material = []
                create_material_vals = []
                for m in data_material_good.get(production_code, []):
                    if not product_dict.get(m[0], False):
                        raise ValidationError(_('Không có Mã vật tư với mã %s trong danh mục sản phẩm.' %m[0]))
                    if not product_dict.get(m[1], False) and m[1] != '':
                        raise ValidationError(_('Không có Mã thành phẩm với mã %s trong danh mục sản phẩm.' %m[1]))
                    if not product_dict.get(m[2], False) and m[2] != '':
                        raise ValidationError(_('Không có NPL thay thế với mã %s trong danh mục sản phẩm.'%m[2]))
                    if not uom_dict.get(m[5], False):
                        raise ValidationError(_('Không có Đvt Lệnh sản xuất %s trong danh mục đơn vị tính.'%m[5]))
                    if m[3] and m[3].strip() not in attributes:
                        raise ValidationError(_('Size %s không tồn tại trong bảng giá trị thuộc tính.' % m[3]))
                    if m[4] and m[4].strip() not in attributes:
                        raise ValidationError(_('Màu %s không tồn tại trong bảng giá trị thuộc tính.' % m[4]))

                    common_data = {
                        'product_id': product_dict.get(m[0], False),
                        'product_finish_id': product_dict.get(m[1], False),
                        'product_backup_id': product_dict.get(m[2], False),
                        'production_uom_id': uom_dict.get(m[5], False),
                        'conversion_coefficient': m[6],
                        'rated_level': m[7],
                        'loss': m[8],
                    }
                    if (m[1].strip() == order[11] or m[1] == '') and (m[3].strip() == '' and m[4].strip() == ''):
                        list_material.append((0, 0, common_data))
                    elif(m[3] and m[3].strip() in product_variant and m[4] and m[4].strip() in product_variant):
                        list_material.append((0, 0, common_data))
                    elif (m[3].strip() in product_variant) and (not m[4] or m[4].strip() == ''):
                        list_material.append((0, 0, common_data))
                    elif (m[4].strip() in product_variant) and (not m[3] or m[3].strip() == ''):
                        list_material.append((0, 0, common_data))
                    elif (not m[3] and not m[4]) and not m[1]:
                        list_material.append((0, 0, common_data))

                    create_material_vals.append((0, 0, {
                        'product_id': product_dict.get(m[0], False),
                        'product_finish_id': product_dict.get(m[1], False),
                        'product_backup_id': product_dict.get(m[2], False),
                        'size': m[3],
                        'color': m[4],
                        'production_uom_id': uom_dict.get(m[5], False),
                        'conversion_coefficient': m[6],
                        'rated_level': m[7],
                        'loss': m[8],
                        'qty': m[9],
                    }))
                create_list_expense = []
                create_list_by_production_expense = []
                for e in data_expense_good.get(production_code, []):
                    if not product_dict.get(e[0], False):
                        raise ValidationError(_('Không có Mã chi phí %s trong danh mục sản phẩm.' % e[0]))
                    cost_norms = 0
                    if float(e[1]) > 0 and e[3]:
                        cost_norms = float(e[3]) / float(e[1])

                    if e[4] == order[11] or not e[4]:
                        create_list_expense.append((0, 0, {
                            'product_id': product_dict.get(e[0], False),
                            'rated_level': cost_norms
                        }))

                    create_list_by_production_expense.append((0, 0, {
                        'product_id': product_dict.get(e[0], False),
                        'quantity': e[1],
                        'cost_norms': cost_norms,
                        'total_cost_norms': e[3],
                        'product_finish_id': product_dict.get(e[4], False),
                    }))

                child_value['forlife_bom_material_ids'] = list_material
                child_value['forlife_bom_service_cost_ids'] = create_list_expense
                child = [(0, 0, child_value)]
                if len(create_list_order) >= 1 and not order[0]:
                    create_list_order[len(create_list_order) - 1]['forlife_production_finished_product_ids'] += child
                else:
                    master['forlife_production_finished_product_ids'] = child
                master['material_import_ids'] = create_material_vals
                master['expense_import_ids'] = create_list_by_production_expense
            if master and master.get('code', False):
                create_list_order.append(master)

        production = self.env['forlife.production'].create(create_list_order)
        action = self.env.ref('forlife_purchase.forlife_production_action').read()[0]
        action['target'] = 'main'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Đã tạo thành công %s bản ghi' % len(production),
                'type': 'success',
                'sticky': False,
                'next': action,
            }
        }
    
    def _check_exist_production(self, code):
        productions = self.env['forlife.production'].search([('code','=', code),('active','=', True)])
        result = False
        for production in productions:
            for line in production.forlife_production_finished_product_ids:
                if line.stock_qty != 0:
                    result = True
        return result


