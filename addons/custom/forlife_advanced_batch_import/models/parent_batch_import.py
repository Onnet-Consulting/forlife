from odoo import api, fields, models
from odoo.addons.base_import.models.base_import import FILE_TYPE_DICT, _logger

from io import BytesIO
import base64
from io import StringIO
import json


class ParentBatchImport(models.Model):
    _name = "parent.batch.import"
    _description = "Manage and configure original file import"
    _rec_name = "display_name"

    display_name = fields.Char(string="Display Name", compute="compute_display_name")
    res_model = fields.Char(string="Model")
    # attachment_id = fields.Many2one(string="Attachment", comodel_name="ir.attachment")
    # binary file
    file = fields.Binary('File', help="File to check and/or import", attachment=True)
    file_name = fields.Char('File Name')
    file_type = fields.Char('File Type')

    list_field = fields.Text(string="List Fields")
    columns = fields.Text(string="Columns")
    options = fields.Text(string="Options")
    dryrun = fields.Boolean(string="Dry Run", help="performs all import operations (and validations) but rollbacks writes, allows getting as much errors as possible without the risk of clobbering the database")
    status = fields.Selection([('draft', 'Draft'), ('processing', 'Processing'), ('done', 'Done'), ('cancel', 'Cancel')], string='Status', default='draft', compute="compute_status")
    limit = fields.Integer(string="Limit records/File")
    number_of_split_file = fields.Integer(string="Number of split file", compute="_compute_number_of_split_file", store=True)
    with_delay = fields.Integer(string="Delay execute between every batch", default=10)
    child_batch_import_ids = fields.One2many(string="Children  Batch", comodel_name="child.batch.import", inverse_name='parent_batch_import_id')
    done_batch_count = fields.Integer(string="Done Batch", compute="compute_batch_count", store=False)
    total_batch = fields.Integer(string="Total Batch", compute="compute_batch_count", store=False)
    progress_bar = fields.Float('Progress Done (%)', digits=(16, 2), compute='compute_batch_count', store=False)
    file_invalid_records = fields.Binary(string="Invalid Records", attachment=True)
    file_invalid_records_name = fields.Char('Invalid records file')
    log = fields.Text(string="Log")

    def merge_file_log_errors(self):
        import pandas as pd
        for rec in self:
            sheet_name = json.loads(rec.options).get('sheet_name') if json.loads(rec.options).get('sheet_name') else "Sheet1"
            mimetype = rec.file_type
            (file_extension, handler, req) = FILE_TYPE_DICT.get(mimetype, (None, None, None))
            if rec.child_batch_import_ids:
                concat_data_frames = []
                for batch in rec.child_batch_import_ids:
                    if batch.file_invalid_records:
                        if file_extension == 'csv':
                            concat_data_frames.append(batch.rec_file_csv(batch.file_invalid_records))
                        else:
                            concat_data_frames.append(batch.rec_file_exel(batch.file_invalid_records))
                if len(concat_data_frames) > 0:
                    merged_df = pd.concat(concat_data_frames, axis=0, ignore_index=True)
                    encoded_output_data = False
                    if file_extension == 'csv':
                        output_data = merged_df.to_csv(index=False)
                        encoded_output_data = base64.b64encode(output_data.encode('utf-8')).decode('utf-8')
                    else:
                        output = BytesIO()
                        writer = pd.ExcelWriter(output, engine='xlsxwriter')
                        merged_df.to_excel(writer, sheet_name=sheet_name, index=False)
                        writer.close()
                        output.seek(0)

                        chunk_data = output.read()
                        encoded_output_data = base64.b64encode(chunk_data)
                    rec.write({
                        'file_invalid_records_name': f"{rec.file_name.split('.')[0]}_invalid_records.{rec.file_name.split('.')[-1]}",
                        'file_invalid_records': encoded_output_data
                    })

    @api.depends('child_batch_import_ids', 'child_batch_import_ids.status')
    def compute_batch_count(self):
        for rec in self:
            total_batch = len(rec.child_batch_import_ids)
            done_batch_count = len(rec.child_batch_import_ids.filtered(lambda b: b.status == 'done'))
            rec.total_batch = total_batch
            rec.done_batch_count = len(rec.child_batch_import_ids.filtered(lambda b: b.status == 'done'))
            rec.progress_bar = (done_batch_count / total_batch) * 100 if total_batch > 0 else 0

    def compute_display_name(self):
        for rec in self:
            rec.display_name = str(rec.res_model) + '_' + str(rec.file_name) + "_" + str(rec.create_date.date())

    def set_all_to_daft(self):
        for rec in self:
            rec.child_batch_import_ids.filtered(lambda b: b.status not in ['draft', 'done']).write({
                'status': 'draft'
            })

    def test_all(self):
        for rec in self:
            rec.child_batch_import_ids.make_queue_test_batch(delay_time=rec.with_delay)

    def set_all_to_processing(self):
        for rec in self:
            rec.child_batch_import_ids.filtered(lambda b: b.status not in ['done']).set_to_processing(delay_time=rec.with_delay)

    @api.depends('child_batch_import_ids', 'child_batch_import_ids.status')
    def compute_status(self):
        for rec in self:
            if all([b.status == 'cancel' for b in rec.child_batch_import_ids]):
                rec.status = 'cancel'
            if all([b.status == 'done' for b in rec.child_batch_import_ids]):
                rec.status = 'done'
            else:
                status = 'draft'
                for batch in rec.child_batch_import_ids:
                    if batch.status == 'processing':
                        status = 'processing'
                        break
                rec.status = status

    @api.depends('child_batch_import_ids')
    def _compute_number_of_split_file(self):
        for rec in self:
            rec.number_of_split_file = len(rec.child_batch_import_ids)

    def create_parent_batch_import(self, fields, columns, options, dryrun=False):
        if options.get('base_import_id'):
            base_import = self.env['base_import.import'].sudo().search([('id', '=', options.get('base_import_id'))], limit=1)
            if base_import:
                batch_import = self.env['parent.batch.import'].sudo().create({
                    'res_model': base_import.res_model,
                    'file': base64.b64encode(base_import.file),
                    'file_name': base_import.file_name,
                    'file_type': base_import.file_type,
                    'list_field': json.dumps(fields),
                    'columns': json.dumps(columns),
                    'options': json.dumps(options),
                    'limit': options.get('limit'),
                    'dryrun': dryrun,
                    'status': 'draft',
                    'with_delay': int(options.get('with_delay')),
                    'number_of_split_file': options.get('split_file'),
                })
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                menu = self.env.ref('forlife_advanced_batch_import.menu_parent_batch_import')
                action = self.env.ref('forlife_advanced_batch_import.parent_batch_import_action')
                dst_url = "%s/web#id=%s&menu_id=%s&action=%s&model=parent.batch.import&view_type=form" % (base_url, batch_import.id, menu.id, action.id)
                if base_import.file_type == 'text/csv':
                    self.split_parent_batch_import_csv(batch_import)
                else:
                    self.split_parent_batch_import_exel(batch_import=batch_import, sheet_name=options.get('sheet_name') if options.get('sheet_name') else "Sheet1")
                # clean base_import.import to release memory before swap to batch import
                base_import.unlink()

                return dst_url
        return False

    def split_parent_batch(self):
        for rec in self:
            mimetype = rec.file_type
            (file_extension, handler, req) = FILE_TYPE_DICT.get(mimetype, (None, None, None))
            try:
                return getattr(rec, 'split_parent_batch_import_' + ('csv' if file_extension == 'csv' else 'exel'))()
            except ValueError as e:
                raise e
            except Exception:
                _logger.error("Failed to split file '%s'", self.file_name or '<unknown>')

    def split_parent_batch_import_csv(self, batch_import=False):
        import pandas as pd
        import numpy as np

        if not batch_import:
            batch_import = self
        # Giải mã nội dung của attachment
        decoded_data = base64.b64decode(batch_import.file)
        # Chuyển decoded_data thành đối tượng StringIO để đọc dữ liệu CSV
        file_data = StringIO(decoded_data.decode('utf-8'))
        # Đọc dữ liệu CSV vào DataFrame
        df = pd.read_csv(file_data)

        # Tính số lượng file con cần tạo
        if len(df) % batch_import.limit == 0:
            num_files = len(df) // batch_import.limit
        else:
            num_files = len(df) // batch_import.limit + 1

        # Chia DataFrame thành các phần nhỏ
        dfs = np.array_split(df, num_files)

        for i, df_part in enumerate(dfs):
            # Chuyển DataFrame thành dạng bytes
            csv_bytes = df_part.to_csv(index=False).encode()

            self.env['child.batch.import'].sudo().create({
                'sequence': i,
                'file': base64.b64encode(csv_bytes),
                'file_type': batch_import.file_type,
                'parent_batch_import_id': batch_import.id,
                # 'attachment_id': att.id,
                'file_name': f"{batch_import.file_name.split('.')[0]}_{i + 1}.{batch_import.file_name.split('.')[-1]}",
                'status': 'draft',
                'skip': 0,
            })

    def split_parent_batch_import_exel(self, batch_import=False, sheet_name='Sheet1'):
        import pandas as pd
        if not batch_import:
            batch_import = self
        # Giải mã nội dung của attachment
        decoded_data = base64.b64decode(batch_import.file)

        # Đọc dữ liệu của attachment vào DataFrame với Pandas
        df = pd.read_excel(BytesIO(decoded_data))

        chunk_size = batch_import.limit
        # Chia DataFrame thành các chunk có số dòng là chunk_size
        chunks = [df[i:i + chunk_size] for i in range(0, df.shape[0], chunk_size)]

        # Lặp qua từng chunk và tạo attachment mới cho mỗi chunk
        for i, chunk in enumerate(chunks):
            # Tạo ExcelWriter để ghi dữ liệu vào file Excel
            output = BytesIO()
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
            chunk.to_excel(writer, sheet_name=sheet_name, index=False)
            writer.close()
            output.seek(0)

            # Lấy dữ liệu đã ghi vào ExcelWriter và chuyển đổi sang dạng bytes
            chunk_data = output.read()
            chunk_data_base64 = base64.b64encode(chunk_data)

            self.env['child.batch.import'].sudo().create({
                'sequence': i,
                'parent_batch_import_id': batch_import.id,
                'file': chunk_data_base64,
                'file_type': batch_import.file_type,
                'file_name': f"{batch_import.file_name.split('.')[0]}_{i + 1}.{batch_import.file_name.split('.')[-1]}",
                'status': 'draft',
                'skip': 0,
            })
