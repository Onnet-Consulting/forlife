# -*- coding:utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError
import xlrd
import base64


class PermissionReportImport(models.TransientModel):
    _name = 'permission.report.import'
    _inherit = 'report.base'
    _description = 'Nhập quyền dữ liệu báo cáo'

    import_file = fields.Binary(attachment=False, string='Tải lên tệp')
    import_file_name = fields.Char()
    error_file = fields.Binary(attachment=False, string='Tệp lỗi')
    error_file_name = fields.Char(default='Error.txt')

    @api.onchange('import_file')
    def onchange_import_file(self):
        self.error_file = False

    @api.model
    def generate_xlsx_report(self, workbook, allowed_company, **kwargs):
        formats = self.get_format_workbook(workbook)
        self._cr.execute("""
with x_model as (select coalesce(name::json ->> 'vi_VN',
                                 name::json ->> 'en_US') as name,
                        model
                 from ir_model
                 where model ilike 'report.num%'
                 order by id),
     x_field as (select model,
                        name,
                        model_id,
                        coalesce(field_description::json ->> 'vi_VN',
                                 field_description::json ->> 'en_US') as description
                 from ir_model_fields
                 where model ilike 'report.num%'
                   and readonly = false
                   and ttype ilike 'many%')
select (select json_object_agg(name, model) from x_model) as model_by_name,
       (select json_object_agg(model, detail)
        from (select model, model_id, json_object_agg(name, description) as detail
              from x_field
              group by model, model_id 
              order by model_id) as x1)                   as field_by_model,
       (select json_object_agg(ru.login, rp.name)
        from res_users ru
                 join res_partner rp on ru.partner_id = rp.id
        where ru.active = true)                           as users
        """)
        result = self._cr.dictfetchone() or {}
        model_by_name = result.get('model_by_name') or {}
        field_by_model = result.get('field_by_model') or {}
        users = result.get('users') or {}

        sheet1 = workbook.add_worksheet('Nhóm quyền')
        sheet1.freeze_panes(1, 0)
        sheet1.set_row(0, 30)
        sheet1.write(0, 0, 'Mã quyền', formats.get('title_format'))
        sheet1.write(0, 1, 'Tên quyền', formats.get('title_format'))
        sheet1.write(0, 2, 'Mã người dùng', formats.get('title_format'))
        sheet1.write(1, 0, 'PQ001', formats.get('normal_format'))
        sheet1.write(1, 1, 'Nhóm quyền siêu cấp promax', formats.get('normal_format'))
        sheet1.write(1, 2, '100000', formats.get('normal_format'))
        sheet1.set_column(0, 2, 20)

        sheet2 = workbook.add_worksheet('Trường dữ liệu được phân quyền')
        sheet2.freeze_panes(1, 0)
        sheet2.set_row(0, 30)
        sheet2.write(0, 0, 'STT', formats.get('title_format'))
        sheet2.write(0, 1, 'Mã định danh', formats.get('title_format'))
        sheet2.write(0, 2, 'Tên báo cáo', formats.get('title_format'))
        sheet2.write(0, 3, 'Mã trường dữ liệu', formats.get('title_format'))
        sheet2.write(0, 4, 'Tên trường dữ liệu', formats.get('title_format'))
        sheet2.write(1, 0, '1', formats.get('normal_format'))
        sheet2.write(1, 1, '1', formats.get('normal_format'))
        sheet2.write(1, 2, 'Báo cáo X', formats.get('normal_format'))
        sheet2.write(1, 3, 'field_x', formats.get('normal_format'))
        sheet2.write(1, 4, 'X', formats.get('normal_format'))
        sheet2.set_column(0, 4, 20)

        sheet3 = workbook.add_worksheet('Khai báo dữ liệu chi tiết')
        sheet3.freeze_panes(1, 0)
        sheet3.set_row(0, 30)
        sheet3.write(0, 0, 'STT', formats.get('title_format'))
        sheet3.write(0, 1, 'Mã định danh', formats.get('title_format'))
        sheet3.write(0, 2, 'Mã trường dữ liệu', formats.get('title_format'))
        sheet3.write(0, 3, 'Dữ liệu', formats.get('title_format'))
        sheet3.write(0, 4, 'Tên mô tả của trường mã dữ liệu', formats.get('title_format'))
        sheet3.write(1, 0, '1', formats.get('normal_format'))
        sheet3.write(1, 1, '1', formats.get('normal_format'))
        sheet3.write(1, 2, 'field_x', formats.get('normal_format'))
        sheet3.write(1, 3, 'K1', formats.get('normal_format'))
        sheet3.write(1, 4, 'Kho K1', formats.get('normal_format'))
        sheet3.set_column(0, 4, 20)

        sheet4 = workbook.add_worksheet('Mapping nhóm quyền - báo cáo')
        sheet4.freeze_panes(1, 0)
        sheet4.set_row(0, 30)
        sheet4.write(0, 0, 'STT', formats.get('title_format'))
        sheet4.write(0, 1, 'Mã quyền', formats.get('title_format'))
        sheet4.write(0, 2, 'Tên quyền', formats.get('title_format'))
        sheet4.write(0, 3, 'Mã định danh', formats.get('title_format'))
        sheet4.write(0, 4, 'Báo cáo', formats.get('title_format'))
        sheet4.write(1, 0, '1', formats.get('normal_format'))
        sheet4.write(1, 1, 'PQ001', formats.get('normal_format'))
        sheet4.write(1, 2, 'Nhóm quyền siêu cấp promax', formats.get('normal_format'))
        sheet4.write(1, 3, '1', formats.get('normal_format'))
        sheet4.write(1, 4, 'Báo cáo X', formats.get('normal_format'))
        sheet4.set_column(0, 4, 20)

        sheet5 = workbook.add_worksheet('Master data Báo cáo')
        sheet5.freeze_panes(1, 0)
        sheet5.set_column(0, 1, 40)
        sheet5.write(0, 0, 'Mã báo cáo', formats.get('title_format'))
        sheet5.write(0, 1, 'Tên báo cáo', formats.get('title_format'))
        i = 1
        for name, model in model_by_name.items():
            sheet5.write(i, 0, model, formats.get('normal_format'))
            sheet5.write(i, 1, name, formats.get('normal_format'))
            i += 1
        i += 1

        sheet6 = workbook.add_worksheet('Master data Trường dữ liệu')
        sheet6.freeze_panes(1, 0)
        sheet6.set_column(0, 2, 30)
        sheet6.write(0, 0, 'Mã báo cáo', formats.get('title_format'))
        sheet6.write(0, 1, 'Mã trường dữ liệu', formats.get('title_format'))
        sheet6.write(0, 2, 'Tên trường dữ liệu', formats.get('title_format'))
        i = 1
        for model, detail in field_by_model.items():
            for field, name in detail.items():
                sheet6.write(i, 0, model, formats.get('normal_format'))
                sheet6.write(i, 1, field, formats.get('normal_format'))
                sheet6.write(i, 2, name, formats.get('normal_format'))
                i += 1
            i += 1

        sheet7 = workbook.add_worksheet('Master data Người dùng')
        sheet7.freeze_panes(1, 0)
        sheet7.set_column(0, 1, 30)
        sheet7.write(0, 0, 'Mã người dùng', formats.get('title_format'))
        sheet7.write(0, 1, 'Tên người dùng', formats.get('title_format'))
        i = 1
        for login, name in users.items():
            sheet7.write(i, 0, login, formats.get('normal_format'))
            sheet7.write(i, 1, name, formats.get('normal_format'))
            i += 1

    def action_import(self):
        self.ensure_one()
        if not self.import_file:
            raise ValidationError("Vui lòng tải lên file mẫu trước khi nhấn nút Nhập !")
        workbook = xlrd.open_workbook(file_contents=base64.decodebytes(self.import_file))
        nhom_quyen = list(self.env['res.utility'].read_xls_book(workbook, 0))[1:]
        truong_du_lieu = list(self.env['res.utility'].read_xls_book(workbook, 1))[1:]
        du_lieu = list(self.env['res.utility'].read_xls_book(workbook, 2))[1:]
        map_quyen_bc = list(self.env['res.utility'].read_xls_book(workbook, 3))[1:]
        if not (nhom_quyen or truong_du_lieu or du_lieu or map_quyen_bc):
            raise ValidationError('Dữ liệu nhập quyền báo cáo rỗng, vui lòng kiểm tra lại !')
        error = []

        # Xử lý sheet Trường dữ liệu được phân quyền
        if truong_du_lieu:
            self._cr.execute("""
                with x_model as (select coalesce(name::json ->> 'vi_VN',
                                                 name::json ->> 'en_US') as name,
                                        id
                                 from ir_model
                                 where model ilike 'report.num%'
                                 order by id),
                     x_field as (select name,
                                        model_id,
                                        id
                                 from ir_model_fields
                                 where model ilike 'report.num%'
                                   and readonly = false
                                   and ttype ilike 'many%')
                select (select json_object_agg(name, id) from x_model)    as model_by_name,
                       (select json_object_agg(model_id, detail)
                        from (select model_id, json_object_agg(name, id) as detail
                              from x_field
                              group by model_id) as x1)                   as field_by_model_id,
                       (select json_object_agg(concat(name, '~', report_id, '~', field_id), id)
                        from res_field_report)                            as field_report_exits
            """)
            result = self._cr.dictfetchone() or {}
            model_by_name = result.get('model_by_name') or {}
            field_by_model_id = result.get('field_by_model_id') or {}
            field_report_exits = result.get('field_report_exits') or {}

            tdl_taomoi = []
            for idx, tdl in enumerate(truong_du_lieu, start=2):
                bao_cao = model_by_name.get(tdl[2])
                if not bao_cao:
                    error.append(f"Sheet Trường dữ liệu được phân quyền, dòng {idx}: Tên báo cáo '{tdl[2]}' không tồn tại trong hệ thống")
                    continue
                truong = (field_by_model_id.get(str(bao_cao)) or {}).get(tdl[3])
                if not truong:
                    error.append(f"Sheet Trường dữ liệu được phân quyền, dòng {idx}: không tồn tại trường '{tdl[3]}' trong báo cáo '{tdl[2]}'")
                    continue
                key = f"{tdl[1]}~{bao_cao}~{truong}"
                if field_report_exits.get(key):
                    continue
                field_report_exits.update({key: -1})
                tdl_taomoi.append({
                    'name': tdl[1],
                    'report_id': bao_cao,
                    'field_id': truong,
                })
            if tdl_taomoi:
                self.env['res.field.report'].create(tdl_taomoi)

        # Xử lý sheet Khai báo dữ liệu chi tiết
        if du_lieu:
            self._cr.execute("""
                with x_value_report as (select name, id
                                        from res_field_value_report
                                        union all
                                        select concat(name, '~', description) as name, id
                                        from res_field_value_report),
                     x_field_report as (select x1.name as name,
                                               x2.name as field,
                                               array_agg(x1.id) as list_id
                                        from res_field_report x1
                                        join ir_model_fields x2 on x1.field_id = x2.id
                                        group by x1.name, x2.name)
                select (select json_object_agg(name, id)
                        from x_value_report) as value_reports,
                       (select json_object_agg(concat(name, '~', field), list_id)
                        from x_field_report) as field_reports
            """)
            result = self._cr.dictfetchone() or {}
            value_reports = result.get('value_reports') or {}
            field_reports = result.get('field_reports') or {}

            dl_taomoi = []
            truong_them_dl = {}
            truong_them_dl_moi = {}

            for idx, dl in enumerate(du_lieu, start=2):
                key1 = f"{dl[1]}~{dl[2]}"
                key2 = f"{dl[3]}~{dl[4]}"
                check_field_report = field_reports.get(key1)
                if not check_field_report:
                    error.append(f"Sheet Khai báo dữ liệu chi tiết, dòng {idx}: Tổ hợp mã định danh/trường dữ liệu '{dl[1]}' - '{dl[2]}' không tồn tại trong hệ thống")
                value = value_reports.get(key2) or value_reports.get(dl[3]) or 0
                if check_field_report:
                    for _id in check_field_report:
                        if value > 0:
                            truong_them_dl.update({_id: (truong_them_dl.get(_id) or []) + [(4, value)]})
                        else:
                            truong_them_dl_moi.update({_id: (truong_them_dl_moi.get(_id) or []) + [dl[3]]})

                if not value:
                    value_reports.update({dl[3]: -1})
                    dl_taomoi.append({
                        'name': dl[3],
                        'description': dl[4],
                    })
            if dl_taomoi:
                value_ids = self.env['res.field.value.report'].create(dl_taomoi)
                self._cr.execute(f"""
                    select json_object_agg(name, id) as value_reports
                    from res_field_value_report
                    where id = any (array {value_ids.ids})
                """)
                x_values = self._cr.dictfetchone() or {}
                x_field_reports = x_values.get('value_reports') or {}
                for k, v in truong_them_dl_moi.items():
                    truong_them_dl.update({k: (truong_them_dl.get(k) or []) + [(4, x_field_reports.get(x_id)) for x_id in v if x_field_reports.get(x_id)]})
            for _id, vals in truong_them_dl.items():
                self.env['res.field.report'].browse(_id).write({'value_ids': vals})

        # Xử lý sheet Nhóm quyền, mapping nhóm quyền - báo cáo
        if nhom_quyen or map_quyen_bc:
            self._cr.execute("""
                with field_reports as (select concat(x1.name, '~', coalesce(x2.name::json ->> 'vi_VN',
                                                                            x2.name::json ->> 'en_US')) as key,
                                              x1.id
                                       from res_field_report x1
                                                join ir_model x2 on x1.report_id = x2.id)
                select (select json_object_agg(login, id) from res_users) as users,
                       (select json_object_agg(concat(code, '~', name), id)
                        from res_group_report)                            as group_report,
                       (select json_object_agg(key, id)
                        from (select key, array_agg(id) as id
                              from field_reports
                              group by key) as s1)                        as mapping_reports
            """)
            result = self._cr.dictfetchone() or {}
            users = result.get('users') or {}
            group_report = result.get('group_report') or {}
            mapping_reports = result.get('mapping_reports') or {}

            nq_ton_tai = {}
            nq_moi = {}
            for idx, nq in enumerate(nhom_quyen, start=2):
                quyen = nq[0] + '~' + nq[1]
                quyen_ton_tai = group_report.get(quyen)
                nguoi_dung = users.get(nq[2])
                if not nguoi_dung:
                    error.append(f"Sheet Nhóm quyền, dòng {idx}: Mã người dùng '{nq[2]}' không tồn tại trong hệ thống")
                if quyen_ton_tai and nguoi_dung:
                    nq_ton_tai.update({quyen_ton_tai: (nq_ton_tai.get(quyen_ton_tai) or []) + [(4, nguoi_dung)]})
                if not quyen_ton_tai and nguoi_dung:
                    nq_moi.update({quyen: (nq_moi.get(quyen) or []) + [nguoi_dung]})
            map_nq_ton_tai = {}
            map_nq_moi = {}
            for idx, val in enumerate(map_quyen_bc, start=2):
                quyen = f"{val[1]}~{val[2]}"
                truong_dl = f"{val[3]}~{val[4]}"
                quyen_ton_tai = group_report.get(quyen)
                _ids = mapping_reports.get(truong_dl)
                if not _ids:
                    error.append(f"Sheet mapping nhóm quyền - báo cáo, dòng {idx}: Mã định danh '{val[3]}' và báo cáo '{val[4]}' không tồn tại trong hệ thống")
                    continue
                if quyen_ton_tai:
                    map_nq_ton_tai.update({quyen_ton_tai: (map_nq_ton_tai.get(quyen_ton_tai) or []) + _ids})
                elif nq_moi.get(quyen):
                    map_nq_moi.update({quyen: (map_nq_moi.get(quyen) or []) + _ids})
                else:
                    error.append(f"Sheet mapping nhóm quyền - báo cáo, dòng {idx}: Mã quyền '{val[1]}' và tên quyền '{val[2]}' không tồn tại trong hệ thống")

            mix_nq_ton_tai = set(list(nq_ton_tai.keys()) + list(map_nq_ton_tai.keys()))
            mix_nq_moi = set(list(nq_moi.keys()) + list(map_nq_moi.keys()))
            for x in mix_nq_ton_tai:
                self.env['res.group.report'].browse(x).write({
                    'user_ids': nq_ton_tai.get(x) or [],
                    'data_permission_ids': [(4, i) for i in (map_nq_ton_tai.get(x) or [])],
                })
            x_val = []
            for x in mix_nq_moi:
                v = x.split('~')
                x_val.append({
                    'code': v[0],
                    'name': v[1],
                    'user_ids': [(6, 0, (nq_moi.get(x) or []))],
                    'data_permission_ids': [(6, 0, (map_nq_moi.get(x) or []))],
                })
            if x_val:
                self.env['res.group.report'].create(x_val)

        if error:
            return self.return_error_log('\n'.join(error))
        return self.env['ir.actions.act_window']._for_xml_id('forlife_report.res_group_report_action')

    def return_error_log(self, error=''):
        self.write({
            'error_file': base64.encodebytes(error.encode()),
            'import_file': False,
        })
        action = self.env['ir.actions.act_window']._for_xml_id('forlife_report.permission_report_import_action')
        action['res_id'] = self.id
        return action
