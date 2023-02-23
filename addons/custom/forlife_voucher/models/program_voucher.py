from odoo import api, fields, models, _
from odoo.exceptions import UserError

Character = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'


class ProgramVoucher(models.Model):
    _name = 'program.voucher'
    _description = 'Program Voucher for Forlife'

    name = fields.Char('Program Voucher Name', required=True)

    program_voucher_code = fields.Char('Voucher Program Code', store=True, copy=False, readonly=True, default='New')

    type = fields.Selection([('v', 'V-Giấy'), ('e', 'E-Điện tử')], string='Type', required=True)

    purpose_id = fields.Many2one('setup.voucher', 'Purpose', required=True)

    derpartment_id = fields.Many2one('hr.department', 'Department Code', required=True)

    apply_many_times = fields.Boolean('Apply many times', default=False)

    apply_contemp_time = fields.Boolean('Áp dụng đồng thời')

    brand_id = fields.Many2one('res.brand', 'Brand', required=True)

    start_date = fields.Datetime('Start date', required=True)

    end_date = fields.Datetime('End date', required=True)

    state_app = fields.Boolean('Trạng thái App')

    store_id = fields.Many2one('store', 'Apply for store', required=True)

    product_id = fields.Many2one('product.template', 'Product Voucher', required=True)

    _sql_constraints = [
        ('product_id_uniq', 'unique(product_id)', 'Only one booth can be linked !'),
    ]

    program_voucher_line_ids = fields.One2many('program.voucher.line', 'program_voucher_id', string='Voucher')
    voucher_ids = fields.One2many('voucher.voucher', 'program_voucher_id')
    voucher_count = fields.Integer('Voucher Count', compute='_compute_count_voucher', store=True)

    @api.depends('voucher_ids')
    def _compute_count_voucher(self):
        for rec in self:
            if rec.voucher_ids:
                rec.voucher_count = len(rec.voucher_ids)
            else:
                rec.voucher_count = 0

    def change_prefix_sequence(self, code: str):
        for i in range(len(Character)):
            if code == Character[i]:
                return Character[i + 1]

    @api.model
    def create(self, vals):
        if 'program_voucher_line_ids' not in vals or not vals['program_voucher_line_ids']:
            raise UserError(_('Please set the infomation of Vourcher!'))
        last_record = self.get_last_sequence()
        if last_record:
            #change character of sequence
            code = last_record.program_voucher_code
            if code[1:] == '999':
                seq = self.env['ir.sequence'].search([('code', '=', 'program.voucher')])
                vals_seq = {
                    'prefix': self.change_prefix_sequence(code[0]),
                    'number_next_actual': 1,

                }
                seq.write(vals_seq)
        if vals.get('program_voucher_code', 'New') == 'New':
            vals['program_voucher_code'] = self.env['ir.sequence'].next_by_code('program.voucher') or 'New'
        return super(ProgramVoucher, self).create(vals)

    def get_last_sequence(self):
        last_record = self.env['program.voucher'].search([], limit=1, order='id desc')
        if last_record:
            return last_record
        return False

    def create_voucher(self):
        if len(self.program_voucher_line_ids) > 0:
            for rec in self.program_voucher_line_ids:
                if rec.partner_ids:
                    for p in rec.partner_ids:
                        for i in range(rec.count):
                            self.env['voucher.voucher'].create({
                                'program_voucher_id': self.id,
                                'state':'new',
                                'partner_id': p.id,
                                'price': rec.price,
                                'price_used':0,
                                'price_residual': rec.price - 0,
                                'derpartment_id': self.derpartment_id.id,
                            })
                if not rec.partner_ids:
                    for i in range(rec.count):
                        self.env['voucher.voucher'].create({
                            'program_voucher_id': self.id,
                            'state': 'new',
                            'price': rec.price,
                            'price_used': 0,
                            'price_residual': rec.price - 0,
                            'derpartment_id': self.derpartment_id.id,
                        })
        else:
            raise UserError(_("Vui lòng thiết lập dữ liệu voucher!"))

    def action_view_voucher_relation(self):
        self.ensure_one()
        return {
            'name': _('Voucher'),
            'domain': [('id', 'in', self.voucher_ids.ids)],
            'res_model': 'voucher.voucher',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'tree,form',
        }




