from odoo import api, fields, models
import json
import base64


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
    file = fields.Binary('File', help="File to check and/or import, raw binary (not base64)", attachment=True)
    file_name = fields.Char('File Name')
    file_type = fields.Char('File Type')
    file_length = fields.Integer(string="File Length")

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
            result = rec.with_delay(channel='import', priority=rec.sequence, eta=rec.parent_batch_import_id.with_delay).batch_execute_import()

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
            rec.log = json.dumps(result, ensure_ascii=False)

    def set_to_processing(self):
        for rec in self:
            rec.status = 'processing'
            rec.log = False
            rec.make_queue_job()
