from odoo import api, fields, models


class ChildBatchImport(models.Model):
    _name = "child.batch.import"
    _description = "Manage sub file and execute import"
    _rec_name = "file"
    _order = "parent_batch_import_id,file,sequence"

    sequence = fields.Integer(string="Sequence", default=1)
    parent_batch_import_id = fields.Many2one(string="Parent Batch", comodel_name="parent.batch.import")
    file = fields.Binary('File', help="File to check and/or import, raw binary (not base64)", attachment=False)
    file_name = fields.Char('File Name')
    skip = fields.Integer(string='Skip')
    status = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('done', 'Done'), ('cancel', 'Cancel')], string='Status', default='pending')
