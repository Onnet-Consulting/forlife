from datetime import datetime

import pytz

from odoo import _, fields, models, api, tools
from odoo.exceptions import Warning as UserError
from odoo.tools import float_is_zero, DEFAULT_SERVER_DATETIME_FORMAT


class PosOrder(models.Model):
    _inherit = "pos.order"

    change_payment_move_ids = fields.Many2many('account.move', readonly=True)
    payment_move_count = fields.Integer(compute='_compute_payment_move')
    has_payment_change = fields.Boolean('Has payment change', readonly=True)
    payment_change_note = fields.Text('Payment change log', readonly=True, default='')

    def _compute_payment_move(self):
        for order in self:
            order.payment_move_count = len(order.change_payment_move_ids)

    @api.model
    def get_valid_methods(self, order_id):
        order = self.browse(order_id)
        methods = order.config_id.payment_method_ids.filtered(lambda m: not m.is_voucher)
        return [{'id': method.id, 'name': method.name} for method in methods]

    @api.model
    def change_payment(self, order_id, payment_lines):
        pos_order = self.browse(int(order_id))
        allow_update = not pos_order.filtered(lambda x: x.session_id.state == "closed")
        if allow_update:
            pos_order.change_payment_not_closed_session(payment_lines)
        else:
            pos_order.change_payment_closed_session(payment_lines)
        return True

    def _prepare_payment_line(self, payment_lines):
        """
        - attr: payment_lines = [{'payment_id': 1, 'payment_method_id': 1, 'amount': 100}, ]
        return dictionary of payment lines: {1: {'payment_method_id': 1, 'amount': 100, 'pos_order_id': 1}
        """
        self.ensure_one()
        precision = self.pricelist_id.currency_id.decimal_places
        payment_change_values = {}
        for line in payment_lines:
            payment = self.env['pos.payment'].browse(line['payment_id'])
            if float_is_zero(line["amount"], precision_digits=precision) or \
                    payment.payment_method_id.id == line['payment_method_id'] or \
                    not line["payment_method_id"]:
                continue
            payment_id = line.pop('payment_id')
            line['pos_order_id'] = self.id
            payment_change_values.update({payment_id: line})
        return payment_change_values

    def change_payment_closed_session(self, payment_lines):
        payment_change_values = self._prepare_payment_line(payment_lines)
        move_line_vals = []
        for payment, new_payment_val in payment_change_values.items():
            payment_id = self.env['pos.payment'].browse(payment)
            previous_method = payment_id.payment_method_id
            new_method = self.env['pos.payment.method'].browse(new_payment_val['payment_method_id'])

            move_line_vals += self._prepare_payment_change_account_move_lines(
                previous_method, new_method, new_payment_val['amount'])

        default_journal = self._get_default_payment_change_journal()
        move_val = {
            'ref': _('Order %s (%s): Payment change') % (self.name, self.session_id.name),
            'currency_id': self.currency_id.id,
            'journal_id': default_journal.id,
            'move_type': 'entry',
            'company_id': self.company_id.id,
            'line_ids': move_line_vals
        }
        move = self.env['account.move'].create(move_val)._post()
        if move:
            note = (self.payment_change_note or '') + (self._get_log_payment_change(payment_change_values) or '')
            self.write({
                'change_payment_move_ids': [[4, move.id] for move in move],
                'has_payment_change': True,
                'payment_change_note': note
            })
        return True

    def change_payment_not_closed_session(self, payment_lines):
        self.ensure_one()
        payment_change_values = self._prepare_payment_line(payment_lines)
        if payment_change_values:
            note = (self.payment_change_note or '') + (self._get_log_payment_change(payment_change_values) or '')
            self.env['pos.payment'].browse(payment_change_values.keys()).unlink()
            for line in payment_change_values.values():
                self.add_payment(line)

            comment = _(
                "The payments of the Order %s (Ref: %s) have been changed by %s on %s") % (
                          self.name, self.pos_reference, self.env.user.name, self._strftime_with_user_tz(datetime.now()))
            self.write({
                'note': '%s\n%s' % (self.note or '', comment),
                'has_payment_change': True,
                'payment_change_note': note
            })
        return True

    def _get_default_payment_change_journal(self):
        return self.company_id.pos_payment_change_journal_id or self.env['account.journal'].search(
            [('company_id', '=', self.company_id.id), ('type', 'in', ['general'])], limit=1)

    def _prepare_payment_change_account_move_lines(self, previous_method, new_method, amount):
        desc = _('Order %s (%s): Payment change %s to %s') % (
            self.name, self.session_id.name, previous_method.name, new_method.name)

        def _move_line(account_id, balance):
            return (0, 0, {
                'name': desc,
                'account_id': account_id,
                'debit': balance > 0 and balance or 0.0,
                'credit': balance < 0 and -balance or 0.0
            })

        debit_account_id = new_method.journal_id.default_account_id.id
        credit_account_id = previous_method.journal_id.default_account_id.id
        move_line_vals = [_move_line(*el)
                          for el in [(debit_account_id, amount),
                                     (credit_account_id, -amount)]]
        return move_line_vals

    def _strftime_with_user_tz(self, time):
        local_tz = pytz.timezone(self.env.user.tz or 'Asia/Ho_Chi_Minh')
        return datetime.strftime(
            pytz.utc.localize(time).astimezone(local_tz), DEFAULT_SERVER_DATETIME_FORMAT
        )

    def _get_log_payment_change(self, payment_change_values):
        logs = ''
        for payment, new_payment_val in payment_change_values.items():
            payment_id = self.env['pos.payment'].browse(payment)
            previous_method = payment_id.payment_method_id
            new_method = self.env['pos.payment.method'].browse(new_payment_val['payment_method_id'])
            formated_amount = tools.format_amount(self.env, new_payment_val['amount'], payment_id.pos_order_id.currency_id)
            logs += '- %s -> %s : %s \n' % (previous_method.name, new_method.name, formated_amount)
        return (logs and _('Payment Change Details (%s):\n') % self._strftime_with_user_tz(datetime.now()) + logs) or ''

    def action_open_move_payment_change(self):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_journal_line")
        action['domain'] = [('id', 'in', self.change_payment_move_ids.ids)]
        return action

    @api.model
    def check_stock_quant_inventory(self, session_id, order_lines):
        session = self.env['pos.session'].browse(session_id)
        stock_location = session.config_id.picking_type_id.default_location_src_id
        product_not_availabel = []
        product_ids = []
        seri_list = []
        for rec in order_lines[0]:
            product_ids.append(rec['product_id'])
            if rec['seri']:
                seri_list.append(rec['seri'])
        if product_ids:
            if len(product_ids) == 1:
                product_ids = str(tuple(product_ids))
                product_ids = product_ids.replace(',', '')
            else:
                product_ids = tuple(product_ids)
        else:
            product_ids = "(null)"
        if seri_list:
            if len(seri_list) == 1:
                seri_list = str(tuple(seri_list))
                seri_list = seri_list.replace(',', '')
            else:
                seri_list = tuple(seri_list)
        else:
            seri_list = "('')"
        sql = f"SELECT pp.id as product_id, pt.detailed_type as detailed_type, stq.id as quant_id, " \
              f"stq.quantity, stq.reserved_quantity, stq.lot_id FROM stock_quant stq " \
              f"JOIN product_product pp ON stq.product_id = pp.id " \
              f"JOIN product_template pt ON pp.product_tmpl_id = pt.id " \
              f"WHERE product_id in {product_ids} and location_id = {stock_location.id} and detailed_type = " \
              f"'product' and (lot_id is null or lot_id in (SELECT id FROM stock_lot WHERE name in {seri_list}) )"
        self._cr.execute(sql)
        data = self._cr.dictfetchall()
        list_product_exits = []
        for rec in order_lines[0]:
            if data:
                for r in data:
                    list_product_exits.append(r['product_id'])
                    if rec['count'] > 0 and rec['product_id'] == r['product_id'] and (r['quantity'] - r['reserved_quantity']) < rec['count']:
                        product_not_availabel.append(rec['product_name'])
        sql_product_id = f"SELECT pp.id, pt.detailed_type FROM product_product as pp JOIN product_template as pt " \
                         f"ON pp.product_tmpl_id = pt.id WHERE pp.id in {product_ids}"
        self._cr.execute(sql_product_id)
        product_types = self._cr.dictfetchall()
        data_product_ids = [x['id'] for x in product_types] if product_types else []
        for rec in order_lines[0]:
            if rec['product_id'] not in list_product_exits and rec['product_id'] not in data_product_ids:
                product_not_availabel.append(rec['product_name'])
        if len(product_not_availabel) > 0:
            message = f"Sản phẩm {', '.join(product_not_availabel)} không đủ tồn trong địa điểm {stock_location.name} kho {stock_location.warehouse_id.name}"
            return message
        return False

