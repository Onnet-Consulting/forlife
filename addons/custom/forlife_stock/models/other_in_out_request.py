from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ForlifeOtherInOutRequest(models.Model):
    _name = 'forlife.other.in.out.request'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Forlife Other In Out Request'

    name = fields.Char(string='Name')
    employee_id = fields.Many2one('hr.employee', string="Employee", default=lambda self: self.env.user.employee_id.id)
    department_id = fields.Many2one('hr.department', string="Department", related='employee_id.department_id')
    partner_id = fields.Many2one('res.partner', string="Partner")
    type_other_id = fields.Many2one('forlife.reason.type', string='Type Other', required=True)
    location_from_id = fields.Many2one('stock.location', string='Location From', required=True)
    location_dest_id = fields.Many2one('stock.location', string='Location To', required=True)
    date_planned = fields.Datetime(string='Date Planned')
    status = fields.Selection([('draft', 'Draft'),
                               ('wait_approve', 'Wait approve'),
                               ('approved', 'Approved'),
                               ('done', 'Done'),
                               ('cancel', 'Cancel'),
                               ('reject', 'Reject')], default='draft')
    other_in_out_request_line_ids = fields.One2many('forlife.other.in.out.request.line', 'other_in_out_request_id', string='Stock Picking')


class ForlifeOtherInOutRequestLine(models.Model):
    _name = 'forlife.other.in.out.request.line'
    _description = 'Forlife Other In Out Request Line'

    other_in_out_request_id = fields.Many2one('forlife.other.in.out.request', ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product', required=True)
    description = fields.Char(string='Description', related="product_id.name")
    asset_id = fields.Many2one('assets.assets', string='Asset')
    date_expected = fields.Datetime(string='Date Expected')
    quantity = fields.Float(string='Quantity')
    uom_id = fields.Many2one(related="product_id.uom_id")
    whs_from_id = fields.Many2one('stock.location', string='Whs From')
    reason_from_id = fields.Many2one('stock.location', string='Reason')
    whs_to_id = fields.Many2one('stock.location', string='Whs To')
    reason_to_id = fields.Many2one('stock.location', string='Reason')
    occasion_id = fields.Many2one('occasion.code', string='Occasion Code')
    production_id = fields.Many2one('forlife.production', string='Production Code')
    cost_center = fields.Many2one('account.analytic.account', string='Production Code')

