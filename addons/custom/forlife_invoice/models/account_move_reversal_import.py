from odoo import api, fields, models, _
from datetime import timedelta, datetime
from odoo.exceptions import ValidationError
import xlrd
import base64


class AccountMoveReversalImport(models.Model):
    _name = 'account.move.reversal.import'
    _description = 'Credit notes import'

    @api.model
    def _get_name_default(self):
        return f"Nhập giấy báo có {(datetime.now() + timedelta(hours=7)).strftime('%d/%m/%Y %H:%M:%S')}"

    name = fields.Char('Name', default=_get_name_default, required=True, copy=False)
    state = fields.Selection(string='State', selection=[('draft', _('Draft')), ('done', _('Done'))], default='draft', copy=False)
    import_file = fields.Binary(attachment=False, string='Import file', copy=False)
    import_file_name = fields.Char(copy=False)
    error_file = fields.Binary(attachment=False, string='Error file', copy=False)
    error_file_name = fields.Char(default=_('ErrorFile.txt'))
    create_date = fields.Datetime('Created on', readonly=True, default=fields.Datetime.now)
    create_uid = fields.Many2one('res.users', 'Created by', readonly=True, default=lambda self: self.env.user)
    invoice_ids = fields.Many2many('account.move', string='Bills', copy=False)
    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company, copy=False)

    def download_template_file(self):
        attachment_id = self.env.ref(f'forlife_invoice.template_import_credit_note')
        return {
            'type': 'ir.actions.act_url',
            'name': 'Get template',
            'url': f'web/content/?model=ir.attachment&id={attachment_id.id}&filename_field=name&field=datas&download=true&name={attachment_id.name}',
            'target': 'new'
        }

    def action_import(self):
        self.ensure_one()
        if not self.import_file:
            raise ValidationError(_('Please upload import file !'))
        workbook = xlrd.open_workbook(file_contents=base64.decodebytes(self.import_file))
        values = list(self.env['res.utility'].read_xls_book(workbook, 0))[1:]
        vals, dong_excel, error = self.prepare_data(values)
        if error:
            return self.log_error_to_file(error)
        if not vals:
            raise ValidationError(_('Import file invalid'))
        so_hd_list = list(dong_excel.keys())
        moves = self.env['account.move'].search([('name', 'in', so_hd_list), ('company_id', '=', self.company_id.id), ('move_type', '=', 'out_invoice'), ('state', '=', 'posted')])
        so_hd_set = set(dong_excel.keys())
        move_name_set = set(moves.mapped('name'))
        if so_hd_set != move_name_set:
            diff = so_hd_set - move_name_set
            for so_dh in diff:
                error.append(f"Dòng {dong_excel.get(so_dh)}, không tìm thấy hóa đơn đã vào sổ có số hợp đồng = '{so_dh}' thuộc công ty '{self.company_id.name}'")
            if error:
                return self.log_error_to_file(error)
        error, credit_notes = self.check_product_invoice_line(vals, moves, dong_excel)
        if error:
            return self.log_error_to_file(error)
        else:
            new_move_ids = self.action_add_credit_note(credit_notes)
            self.write({'state': 'done', 'invoice_ids': new_move_ids})

    @api.model
    def prepare_data(self, values):
        error = []
        vals = {}
        dong_excel = {}
        for index, line in enumerate(values):
            so_hoa_don_goc = line[0].strip()
            so_dong = int(line[1]) if line[1] else None
            ma_san_pham = line[2].strip()
            don_gia = int(line[4]) if line[4] else 0
            pt_chiet_khau = float(line[5]) if line[5] else 0
            chiet_khau = int(line[6]) if line[6] else 0
            if not so_hoa_don_goc:
                error.append(f"Dòng {index + 2}, Số hóa đơn gốc không hợp lệ")
            if not ma_san_pham:
                error.append(f"Dòng {index + 2}, Mã sản phẩm không hợp lệ")
            if not error:
                vals.update({
                    so_hoa_don_goc: (vals.get(so_hoa_don_goc) or []) + [{
                        'so_dong': so_dong,
                        'ma_san_pham': ma_san_pham,
                        'don_gia': don_gia,
                        'pt_chiet_khau': pt_chiet_khau,
                        'chiet_khau': chiet_khau,
                        'dong': index + 2,
                    }]
                })
                dong_excel.update({
                    so_hoa_don_goc: (dong_excel.get(so_hoa_don_goc) or []) + [index + 2]
                })
        return None if error else vals, None if error else dong_excel, error

    @api.model
    def check_product_invoice_line(self, vals, moves, dong_excel):
        error = []
        credit_notes = []
        for key, value in vals.items():
            move = moves.filtered(lambda s: s.name == key)
            if not move:
                error.append(f"Dòng {dong_excel.get(key)}, không tìm thấy hóa đơn đã vào sổ có số hợp đồng = '{key}' thuộc công ty '{self.company_id.name}'")
                continue
            if len(move) > 1:
                error.append(f"Dòng {dong_excel.get(key)}, tìm thấy {len(move)} hóa đơn đã vào sổ có số hợp đồng = '{key}' thuộc công ty '{self.company_id.name}'")
                continue
            for detail in value:
                so_dong = detail.get('so_dong') or None
                if so_dong:
                    try:
                        invoice_line = move.invoice_line_ids[so_dong - 1]
                        if invoice_line.product_id.barcode != detail.get('ma_san_pham'):
                            error.append(f"Dòng {detail.get('dong')}, mã sản phẩm {detail.get('ma_san_pham')} không khớp với mã sản phẩm có số dòng = {so_dong} trên hóa đơn gốc")
                    except Exception as e:
                        error.append(f"Dòng {detail.get('dong')}, số dòng = {so_dong} trên hóa đơn gốc không hợp lệ")
                else:
                    invoice_line = move.filtered(lambda s: s.product_id.barcode == detail.get('ma_san_pham'))
                    if not invoice_line:
                        error.append(f"Dòng {detail.get('dong')}, không tìm thấy chi tiết hóa đơn có mã sản phẩm = '{detail.get('ma_san_pham')}' trong hóa đơn gốc {key}")
                        continue
                    if len(invoice_line) > 1:
                        error.append(f"Dòng {dong_excel.get(key)}, tìm thấy {len(invoice_line)} chi tiết hóa đơn có mã sản phẩm = '{detail.get('ma_san_pham')}' trong hóa đơn gốc {key}")
                        continue
            if not error:
                credit_notes.append((move, value))
        return error, None if error else credit_notes

    @api.model
    def action_add_credit_note(self, credit_notes):
        new_move_ids = []
        for (move, data) in credit_notes:
            move_reversal = self.env['account.move.reversal'].sudo().with_context(active_ids=move.ids, active_model='account.move').create({
                'reason': 'Hóa đơn điều chỉnh',
                'journal_id': move.journal_id.id,
            })
            res = move_reversal.reverse_moves()
            new_move = self.env['account.move'].browse(res['res_id'])
            write_line = []
            for item in data:
                so_dong = item.get('so_dong') or None
                if so_dong:
                    line = new_move.invoice_line_ids[so_dong - 1]
                    if line:
                        line.write({
                            'price_unit': item.get('don_gia') or 0,
                            'discount': item.get('pt_chiet_khau') or 0,
                            'discount_percent': item.get('chiet_khau') or 0,
                        })
                        write_line.extend(line.ids)
                else:
                    line = new_move.invoice_line_ids.filtered(lambda s: s.product_id.barcode == item.get('ma_san_pham'))
                    if line:
                        line.write({
                            'price_unit': item.get('don_gia') or 0,
                            'discount': item.get('pt_chiet_khau') or 0,
                            'discount_percent': item.get('chiet_khau') or 0,
                        })
                        write_line.extend(line.ids)
            new_move.invoice_line_ids.filtered(lambda s: s.id not in write_line).sudo().unlink()
            new_move_ids.append((4, new_move.id))
        return new_move_ids

    def log_error_to_file(self, error):
        self.write({
            'error_file': base64.encodebytes('\n'.join(error).encode()),
        })
        return False

    def unlink(self):
        if 'done' in self.mapped('state'):
            raise ValidationError('Không thể xóa bản ghi ở trạng thái hoàn thành.')
        return super().unlink()
