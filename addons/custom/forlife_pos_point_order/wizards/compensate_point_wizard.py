from odoo import _, api, fields, models
from dateutil.relativedelta import relativedelta


class CompensatePointWizard(models.TransientModel):
    _name = "compensate.point.wizard"
    _description = 'Compensate Point Wizard'

    partner_id = fields.Many2one('res.partner', required=True)
    date_order = fields.Datetime('Date Order', required=True)
    points_fl_order = fields.Integer('Points Order', required=True)
    reason = fields.Text('Reason', required=True)
    type = fields.Selection([('forlife', "Forlife"), ('format', "Format")])

    @api.model
    def default_get(self, fields):
        res = super(CompensatePointWizard, self).default_get(fields)
        res.update({'partner_id': self._context.get('active_id')})
        return res

    def action_confirm(self):
        history_point_obj = self.env['partner.history.point']
        account_move_obj = self.env['account.move']
        code_search = 'TKL' if self.type == 'forlife' else 'FMT'
        brand_id = self.env['res.brand'].search([('code', '=', code_search)], limit=1)
        point_promotion_id = self.env['points.promotion'].search([('brand_id', '=', brand_id.id), ('state', '=', 'in_progress')], limit=1)

        if point_promotion_id:
            # Create history point - compensate point
            history_point_obj.create({
                'partner_id': self.partner_id.id,
                'point_order_type': 'point compensate',
                'store': self.type,
                'create_date': self.date_order,
                'date_order': self.date_order,
                'points_fl_order': self.points_fl_order,
                'points_store': self.points_fl_order,
                'reason': self.reason
            })

            # Create journal entry
            move_line_vals = [(0, 0, {
                'account_id': point_promotion_id.point_customer_id.property_account_receivable_id.id,
                'partner_id': point_promotion_id.point_customer_id.id,
                'name': self.partner_id.name,
                'credit': self.points_fl_order * 1000,
                'debit': 0
            })]
            move_line_vals += [(0, 0, {
                'account_id': point_promotion_id.acc_accumulate_points_id.id,
                'debit': self.points_fl_order * 1000,
                'credit': 0,
            })]
            ref = "TokyoLife" if self.type == 'forlife' else self.type.title()
            move_vals = {
                'ref': ref,
                'date': self.date_order.date(),
                'journal_id': point_promotion_id.account_journal_id.id,
                'line_ids': move_line_vals,
                'point_order_type': 'point compensate'
            }
            account_move_obj.create(move_vals).sudo().action_post()

            # Update reset date
            new_reset_date = self.date_order + relativedelta(days=point_promotion_id.point_expiration)
            if self.type == 'forlife':
                reset_vals = {'reset_day_of_point_forlife': new_reset_date}
            else:
                reset_vals = {'reset_day_of_point_format': new_reset_date}

            self.partner_id.write(reset_vals)
