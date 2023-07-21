# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import xlrd
import base64


class ImportInventorySessionWizard(models.TransientModel):
    _name = 'import.inventory.session.wizard'
    _description = 'Import Inventory Session'

    import_file = fields.Binary(attachment=False, string='Tải lên tệp')
    import_file_name = fields.Char()
    error_file = fields.Binary(attachment=False, string='Tệp lỗi')
    error_file_name = fields.Char(default='Error.txt')
    inv_id = fields.Many2one('stock.inventory', 'Phiếu kiểm kê')

    def download_template_file(self):
        attachment_id = self.env.ref(f'stock_inventory.{self._context.get("template_xml_id")}')
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
        if not self.import_file:
            raise ValidationError("Vui lòng tải lên file mẫu trước khi nhấn nút import !")
        workbook = xlrd.open_workbook(file_contents=base64.decodebytes(self.import_file))
        values = list(self.env['res.utility'].read_xls_book(workbook, 0))[self._context.get('start_row') or 1:]
        return getattr(self, self._context.get('template_xml_id').replace('template', ''), None)(values)

    def _import_inventory_session_add(self, values):
        self._cr.execute(f"""
            select json_object_agg(barcode, id) as products from product_product where barcode notnull and barcode <> ''
        """)
        data = self._cr.dictfetchone()
        products = data.get('products') or {}
        vals = []
        error = []
        for index, val in enumerate(values):
            product_id = products.get(val[0])
            phien_dem_bo_sung = float(val[1] or 0)
            if not product_id:
                error.append(f"Dòng {index + 1}, không tìm thấy sản phẩm có mã là '{val[0]}'")
            if not error:
                vals.append((0, 0, {
                    'product_id': product_id,
                    'phien_dem_bo_sung': phien_dem_bo_sung
                }))
        if error:
            return self.return_error_log('\n'.join(error))
        return self._action_import(vals) if vals else False

    def _import_inventory_session_add2(self, values):
        self._cr.execute(f"""
            select json_object_agg(barcode, id) as products from product_product where barcode notnull and barcode <> ''
        """)
        data = self._cr.dictfetchone()
        products = data.get('products') or {}
        vals = []
        error = []
        for index, val in enumerate(values):
            product_id = products.get(val[0])
            them2 = float(val[1] or 0)
            bot2 = float(val[2] or 0)
            if not product_id:
                error.append(f"Dòng {index + 1}, không tìm thấy sản phẩm có mã là '{val[0]}'")
            if not error:
                vals.append((0, 0, {
                    'product_id': product_id,
                    'them2': them2,
                    'bot2': bot2,
                }))
        if error:
            return self.return_error_log('\n'.join(error))
        return self._action_import(vals) if vals else False

    def _import_inventory_session_other(self, values):
        self._cr.execute(f"""
            select json_object_agg(barcode, id) as products from product_product where barcode notnull and barcode <> ''
        """)
        data = self._cr.dictfetchone()
        products = data.get('products') or {}
        vals = []
        error = []
        for index, val in enumerate(values):
            product_id = products.get(val[0])
            hang_khong_kiem_dem = float(val[1] or 0)
            tui_ban_hang = float(val[2] or 0)
            hang_khong_tem = float(val[3] or 0)
            hang_khong_cheat_duoc = float(val[4] or 0)
            hang_loi_chua_duyet = float(val[5] or 0)
            hang_loi_da_duyet = float(val[6] or 0)
            them1 = float(val[7] or 0)
            bot1 = float(val[8] or 0)
            cong_hang_ban_ntl_chua_kiem = float(val[9] or 0)
            tru_hang_ban_da_kiem = float(val[10] or 0)
            bo_sung_hang_chua_cheat = float(val[11] or 0)
            tru_hang_kiem_dup = float(val[12] or 0)
            note = val[13]
            if not product_id:
                error.append(f"Dòng {index + 1}, không tìm thấy sản phẩm có mã là '{val[0]}'")
            if not error:
                vals.append((0, 0, {
                    'product_id': product_id,
                    'hang_khong_kiem_dem': hang_khong_kiem_dem,
                    'tui_ban_hang': tui_ban_hang,
                    'hang_khong_tem': hang_khong_tem,
                    'hang_khong_cheat_duoc': hang_khong_cheat_duoc,
                    'hang_loi_chua_duyet': hang_loi_chua_duyet,
                    'hang_loi_da_duyet': hang_loi_da_duyet,
                    'them1': them1,
                    'bot1': bot1,
                    'cong_hang_ban_ntl_chua_kiem': cong_hang_ban_ntl_chua_kiem,
                    'tru_hang_ban_da_kiem': tru_hang_ban_da_kiem,
                    'bo_sung_hang_chua_cheat': bo_sung_hang_chua_cheat,
                    'tru_hang_kiem_dup': tru_hang_kiem_dup,
                    'note': note,
                }))
        if error:
            return self.return_error_log('\n'.join(error))
        return self._action_import(vals) if vals else False

    def _action_import(self, vals):
        res = self.env['inventory.session'].sudo().create({
            'inv_id': self.inv_id.id,
            'line_ids': vals,
        })
        action = self.env.ref('stock_inventory.inventory_session_form_view_action').read()[0]
        action['res_id'] = res.id
        return action

    def return_error_log(self, error=''):
        self.write({
            'error_file': base64.encodebytes(error.encode()),
            'import_file': False,
        })
        action = self.env.ref('stock_inventory.import_inventory_session_action').read()[0]
        action['res_id'] = self.id
        return action
