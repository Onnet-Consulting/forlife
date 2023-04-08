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
    attachment_id = fields.Many2one(string="Attachment", comodel_name="ir.attachment")
    file_name = fields.Char('File Name')
    skip = fields.Integer(string='Skip')
    log = fields.Text(string="Log")
    status = fields.Selection([('draft', 'Draft'), ('processing', 'Processing'), ('done', 'Done'), ('error', 'Error'), ('cancel', 'Cancel')], string='Status', default='draft')

    def make_queue_job(self):
        for rec in self:
            # tạo job queue theo sequence và delay time
            result = rec.with_delay(priority=rec.sequence, eta=rec.parent_batch_import_id.with_delay).batch_execute_import()

    def batch_execute_import(self):
        for rec in self:
            try:
                base_import_from_batch = self.env['base_import.import'].sudo().create({
                    'file': base64.b64decode(rec.attachment_id.datas),
                    'file_name': rec.file_name,
                    'file_type': rec.attachment_id.mimetype,
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
                    rec.status = 'done'
                    rec.log = json.dumps(result, ensure_ascii=False)
                else:
                    rec.status = 'error'
                    rec.log = json.dumps(result, ensure_ascii=False)
            except Exception as e:
                rec.status = 'error'
                rec.log = str(e)

    def test_execute_import(self):
        for rec in self:
            base_import_from_batch = self.env['base_import.import'].sudo().create({
                'file': base64.b64decode(rec.attachment_id.datas),
                'file_name': rec.file_name,
                'file_type': rec.attachment_id.mimetype,
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
