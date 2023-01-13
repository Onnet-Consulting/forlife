from odoo import api, fields, models, _


class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Purchase Request"

    name = fields.Char(string="Request name", required=True, default='New')
    # wo_code = fields.Char(string="Work Order Code")
    user_id = fields.Many2one('res.users', string="User Requested", required=True, default=lambda self: self.env.user)
    employee_id = fields.Many2one(related='user_id.employee_id', string='Employee')
    department_id = fields.Many2one(related='user_id.department_id')
    date_planned = fields.Datetime(string='Expected Arrival')
    request_date = fields.Date(string='Request date')
    order_lines = fields.One2many('purchase.request.line', 'request_id', )
    order_ids = fields.One2many('purchase.order', 'request_id')

    state = fields.Selection(
        default='draft',
        string="Status",
        selection=[('draft', 'draft'),
                   ('open', 'open'),
                   ('confirm', 'confirm'),
                   ('approved', 'approved'),
                   ('done', 'done'),
                   ('sale', 'Sale Order'),
                   ('reject', 'reject'),
                   ('cancel', 'cancel'),
                   ])
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True,
                                 default=lambda self: self.env.company.id)
    approval_logs_ids = fields.One2many('approval.logs', 'purchase_request_id')

    def submit_to_Approved_action(self):
        for record in self:
            record.write({'state': 'open'})

    def cancel_action(self):
        for record in self:
            record.write({'state': 'cancel'})

    def approve_action(self):
        template_id = self.env.ref('purchase_request.approve_purchase_email_template').id
        template = self.env['mail.template'].browse(template_id)
        category = self.env.ref('base.module_category_inventory_purchase', raise_if_not_found=False)
        users = self.env['res.groups'].search([('category_id', '=', category.id)]).users
        for u in users:
            if u.id != self._uid:
                template.write({'email_to': u.id})
        template.send_mail(self.id, force_send=True)
        self.write({'state': 'approved'})

    def confirm_reject(self):
        for record in self:
            record.write({'state': 'reject'})

    def reset_action(self):
        for record in self:
            record.write({'state': 'draft'})

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Download Template for Purchase Request'),
            'template': '/purchase_request/static/src/xlsx/template_pr.xlsx?download=true'
        }]

    def orders_smart_button(self):
        return {
            'name': 'Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_id': False,
            'view_mode': 'tree,form',
            'domain': [('request_id', '=', self.id)],
        }

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('purchase.request.name.sequence') or 'Pr'
        return super(PurchaseRequest, self).create(vals)

    def action_create_purchase_order(self):
        for r in self:
            list_consumable = []
            list_service = []
            list_product = []
            # for line in r.order_lines:
            #     if line.product_id.detailed_type == 'consu' and r.state == 'approved':
            #         list_consumable.append(line.product_id.id)
            #         r.state = 'sale'
            #     elif line.product_id.detailed_type == 'service' and r.state == 'approved':
            #         list_service.append(line.product_id.id)
            #         r.state = 'sale'
            #     else:
            #         list_product.append(line.product_id.id)
            #         r.state = 'sale'
            # if list_consumable:
            #     for item in list_consumable:
            #         self.env['purchase.order'].create({
            #             'product_id': item,
            #             'state': 'purchase'
            #         })


class PurchaseRequestLine(models.Model):
    _name = "purchase.request.line"
    _description = "Purchase Request Line"

    product_id = fields.Many2one('product.product', string="Product", required=True)
    product_type = fields.Selection(related='product_id.detailed_type', string='Type')
    asset_description = fields.Char(string="Asset description")
    quantity = fields.Float(default=1, string='Quantity')
    uom_id = fields.Many2one('uom.uom', string='Purchase Unit')
    secondary_quantity = fields.Float('Quantity of Exchange', digits='Product Unit of Measure')
    vendor_code = fields.Char(string="Vendor Code")
    production_id = fields.Many2one('forlife.production', string='Production Order Code')
    request_id = fields.Many2one('purchase.request')
    date_planned = fields.Datetime(string='Expected Arrival')
    request_date = fields.Date(string='Request date')


class ApprovalLogs(models.Model):
    _name = 'approval.logs'
    _description = 'Approval Logs'

    purchase_request_id = fields.Many2one('purchase.request', ondelete='cascade')
    request_approved_date = fields.Date('Request Approved')
    approval_user_id = fields.Many2one('res.users')
    function = fields.Char(related='approval_user_id.function')  # Job Position in res.user
    note = fields.Text()
    state = fields.Selection(
        default='draft',
        string="Status",
        selection=[('draft', 'draft'),
                   ('open', 'open'),
                   ('confirm', 'confirm'),
                   ('approved', 'approved'),
                   ('done', 'done'),
                   ('reject', 'reject'),
                   ('cancel', 'cancel'),
                   ])
