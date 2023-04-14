from odoo import api, fields, models
import json
import base64
from io import StringIO
from io import BytesIO
from odoo.addons.base_import.models.base_import import FILE_TYPE_DICT, _logger


class ChildBatchImport(models.Model):
    _name = "child.batch.import"
    _description = "Manage sub file and execute import"
    _rec_name = "file_name"
    _order = "parent_batch_import_id,sequence"

    sequence = fields.Integer(string="Sequence", default=1)
    parent_batch_import_id = fields.Many2one(string="Parent Batch", comodel_name="parent.batch.import", ondelete='cascade')
    skip = fields.Integer(string='Skip')
    log = fields.Text(string="Log")
    status = fields.Selection([('draft', 'Draft'), ('processing', 'Processing'), ('done', 'Done'), ('error', 'Error'), ('cancel', 'Cancel')], string='Status', default='draft')
    complete_records = fields.Integer(string="Complete Records")
    error_rows = fields.Text(string="Error Rows")
    progress_bar = fields.Float('Progress Done (%)', digits=(16, 2), compute='_compute_progress_bar')
    # binary file
    file = fields.Binary('File', help="File to check and/or import", attachment=True)
    file_name = fields.Char('File Name')
    file_type = fields.Char('File Type')
    file_length = fields.Integer(string="File Length")
    file_invalid_records = fields.Binary(string="Invalid Records", attachment=True)
    file_invalid_records_name = fields.Char('Invalid records file')

    @api.depends('complete_records', 'file_length')
    def _compute_progress_bar(self):
        for rec in self:
            complete = 0
            if rec.complete_records and rec.file_length > 0:
                complete = (rec.complete_records / int(rec.file_length)) * 100
            rec.progress_bar = complete

    def make_queue_job(self):
        for rec in self:
            # tạo job queue theo sequence và delay time
            result = rec.with_delay(priority=rec.sequence, eta=rec.parent_batch_import_id.with_delay).batch_execute_import()

    def batch_execute_import(self):
        for rec in self:
            try:
                base_import_from_batch = self.env['base_import.import'].sudo().create({
                    'file': base64.b64decode(rec.file),
                    'file_name': rec.file_name,
                    'file_type': rec.file_type,
                    'res_model': rec.parent_batch_import_id.res_model,
                })
                # trong trường hợp không phải là file nhỏ đầu tiên, thì sẽ không có has_headers
                options = json.loads(rec.parent_batch_import_id.options)
                # if options.get('has_headers') and rec.sequence > 0:
                #     options['has_headers'] = False
                fields = json.loads(rec.parent_batch_import_id.list_field)
                columns = json.loads(rec.parent_batch_import_id.columns)
                # execute dựa vào hàm base của base_import.import
                result = base_import_from_batch.execute_import(fields=fields, columns=columns,
                                                               options=options,
                                                               dryrun=rec.parent_batch_import_id.dryrun)
                if result.get('ids') and len(result.get('messages')) == 0:
                    rec.write({
                        'status': 'done',
                        'log': json.dumps(result, ensure_ascii=False),

                    })

                else:
                    rec.status = 'error'
                    rec.log = json.dumps(result, ensure_ascii=False)
                index_for_header = 2 if options.get('has_headers') else 1
                error_rows = list(dict.fromkeys([int(row.get('record')) + index_for_header for row in (result.get('messages') if result.get('messages') else [])]))
                file_length = result.get('file_length') if result.get('file_length') else rec.parent_batch_import_id.limit
                if len(error_rows) > 0:
                    rec.write({
                        'error_rows': json.dumps(error_rows),
                        'complete_records': file_length - len(error_rows) if rec.file_length > 0 else 0,
                        'file_length': file_length
                    })
                else:
                    rec.write({
                        'error_rows': False,
                        'complete_records': rec.file_length,
                        'file_length': file_length
                    })
                rec.make_file_log_invalid_records()
            except Exception as e:
                rec.status = 'error'
                rec.log = str(e)

    def test_execute_import(self):
        for rec in self:
            base_import_from_batch = self.env['base_import.import'].sudo().create({
                'file': base64.b64decode(rec.file),
                'file_name': rec.file_name,
                'file_type': rec.file_type,
                'res_model': rec.parent_batch_import_id.res_model,
            })
            options = json.loads(rec.parent_batch_import_id.options)
            fields = json.loads(rec.parent_batch_import_id.list_field)
            columns = json.loads(rec.parent_batch_import_id.columns)
            result = base_import_from_batch.execute_import(fields=fields, columns=columns,
                                                           options=options,
                                                           dryrun=True)
            index_for_header = 2 if options.get('has_headers') else 1
            error_rows = list(dict.fromkeys([int(row.get('record')) + index_for_header for row in (result.get('messages') if result.get('messages') else [])]))
            file_length = result.get('file_length') if result.get('file_length') else rec.parent_batch_import_id.limit
            if len(error_rows) > 0:
                rec.write({
                    'error_rows': json.dumps(error_rows),
                    'file_length': file_length,
                    'log': json.dumps(result, ensure_ascii=False)
                })
            else:
                rec.write({
                    'error_rows': False,
                    'file_length': file_length,
                    'log': json.dumps(result, ensure_ascii=False)
                })
            rec.make_file_log_invalid_records()

    def set_to_processing(self):
        for rec in self:
            rec.status = 'processing'
            rec.log = False
            rec.make_queue_job()

    def make_file_log_invalid_records(self):
        for rec in self:
            mimetype = rec.file_type
            (file_extension, handler, req) = FILE_TYPE_DICT.get(mimetype, (None, None, None))
            try:
                return getattr(rec, 'make_file_log_invalid_records_' + ('csv' if file_extension == 'csv' else 'exel'))()
            except ValueError as e:
                raise e
            except Exception:
                _logger.warning("Failed make log file for origin file '%s' (transient id %d) using guessed mimetype %s", self.file_name or '<unknown>')

    def make_file_log_invalid_records_csv(self):
        import pandas as pd
        for rec in self:
            error_rows = list(dict.fromkeys([int(row.get('record')) for row in (json.loads(rec.log).get('messages') if json.loads(rec.log).get('messages') else [])]))
            if len(error_rows) > 0 and rec.file:
                decoded_data = base64.b64decode(rec.file)
                df = pd.read_csv(StringIO(decoded_data.decode('utf-8')))
                # Lọc các hàng cần giữ lại
                filtered_df = df[df.index.isin(error_rows)]

                output_data = filtered_df.to_csv(index=False)
                encoded_output_data = base64.b64encode(output_data).decode('utf-8')
                rec.write({
                    'file_invalid_records_name': f"{rec.file_name.split('.')[0]}_invalid_records.{rec.file_name.split('.')[-1]}",
                    'file_invalid_records': encoded_output_data
                })

    def make_file_log_invalid_records_exel(self):
        import pandas as pd
        for rec in self:
            error_rows = list(dict.fromkeys([int(row.get('record')) for row in (json.loads(rec.log).get('messages') if json.loads(rec.log).get('messages') else [])]))
            sheet_name = json.loads(rec.parent_batch_import_id.options).get('sheet_name') if json.loads(rec.parent_batch_import_id.options).get('sheet_name') else "Sheet1"
            if len(error_rows) > 0 and rec.file:
                decoded_data = base64.b64decode(rec.file)
                df = pd.read_excel(BytesIO(decoded_data))
                # Lọc các hàng cần giữ lại
                filtered_df = df[df.index.isin(error_rows)]
                output = BytesIO()
                writer = pd.ExcelWriter(output, engine='xlsxwriter')
                filtered_df.to_excel(writer, sheet_name=sheet_name, index=False)
                writer.close()
                output.seek(0)

                chunk_data = output.read()
                chunk_data_base64 = base64.b64encode(chunk_data)
                rec.write({
                    'file_invalid_records_name': f"{rec.file_name.split('.')[0]}_invalid_records.{rec.file_name.split('.')[-1]}",
                    'file_invalid_records': chunk_data_base64
                })
