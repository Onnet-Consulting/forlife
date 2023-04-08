from odoo import api, fields, models
import json
import base64


class ChildBatchImport(models.Model):
    _name = "child.batch.import"
    _description = "Manage sub file and execute import"
    _rec_name = "file_name"
    _order = "parent_batch_import_id,sequence"

    sequence = fields.Integer(string="Sequence", default=1)
    parent_batch_import_id = fields.Many2one(string="Parent Batch", comodel_name="parent.batch.import")
    attachment_id = fields.Many2one(string="Attachment", comodel_name="ir.attachment")
    file_name = fields.Char('File Name')
    skip = fields.Integer(string='Skip')
    log = fields.Text(string="Log")
    status = fields.Selection([('draft', 'Draft'), ('processing', 'Processing'), ('done', 'Done'), ('error', 'Error'), ('cancel', 'Cancel')], string='Status', default='draft')

    def write(self, values):
        res = super(ChildBatchImport, self).write(values)
        if 'status' in values and values.get('status') == 'processing':
            for rec in self:
                rec.make_queue_job()
        return res

    def make_queue_job(self):
        for rec in self:
            # tạo job queue theo sequence và delay time
            result = rec.with_delay(priority=rec.sequence, eta=rec.parent_batch_import_id.with_delay).batch_execute_import(fields=json.loads(rec.parent_batch_import_id.list_field), columns=json.loads(rec.parent_batch_import_id.columns),
                                                                                                                           options=json.loads(rec.parent_batch_import_id.options),
                                                                                                                           dryrun=rec.parent_batch_import_id.dryrun)

    def batch_execute_import(self, fields, columns, options, dryrun=False):
        for rec in self:
            base_import_from_batch = self.env['base_import.import'].sudo().create({
                'file': rec.attachment_id.datas,
                'file_name': rec.file_name,
                'file_type': rec.attachment_id.mimetype,
                'res_model': rec.parent_batch_import_id.res_model,
            })
            # trong trường hợp không phải là file nhỏ đầu tiên, thì sẽ không có has_headers
            options = json.loads(rec.parent_batch_import_id.options)
            if options.get('has_headers') and rec.sequence != 1:
                options['has_headers'] = False
            # execute dựa vào hàm base của base_import.import
            result = base_import_from_batch.execute_import(fields=json.loads(rec.parent_batch_import_id.list_field), columns=json.loads(rec.parent_batch_import_id.columns),
                                                           options=options,
                                                           dryrun=rec.parent_batch_import_id.dryrun)
            if result.get('ids') and len(result.get('messages')) == 0:
                rec.status = 'done'
            else:
                rec.status = 'error'
                rec.log = json.dumps(result, ensure_ascii=False)

    def test_execute_import(self):
        for rec in self:
            base_import_from_batch = self.env['base_import.import'].sudo().create({
                'file': base64.b64decode(rec.attachment_id.datas),
                'file_name': rec.file_name,
                'file_type': rec.attachment_id.mimetype,
                'res_model': rec.parent_batch_import_id.res_model,
            })
            result = base_import_from_batch.execute_import(fields=json.loads(rec.parent_batch_import_id.list_field), columns=json.loads(rec.parent_batch_import_id.columns), options=json.loads(rec.parent_batch_import_id.options), dryrun=True)
            rec.log = json.dumps(result, ensure_ascii=False)

    def set_to_processing(self):
        for rec in self:
            rec.status = 'processing'
            rec.make_queue_job()
