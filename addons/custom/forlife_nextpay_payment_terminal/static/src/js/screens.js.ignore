odoo.define('forlife_pos_payment_terminal.screen', function (require) {
    'use strict';

    var screens = require("point_of_sale.screens");
    var core = require("web.core");
    var gui = require("point_of_sale.gui");
    var popups = require("point_of_sale.popups");
    var QWeb = core.qweb;
    var rpc = require("web.rpc");
    var chrome = require("point_of_sale.chrome");
    var PosBaseWidget = require("point_of_sale.BaseWidget");
    var utils = require("web.utils");
    var _t = core._t;


    screens.PaymentScreenWidget.include({
        click_delete_paymentline: function (cid) {
            var self = this;
            var lines = this.pos.get_order().get_paymentlines();
            for (var i = 0; i < lines.length; i++) {
                var line = lines[i];
                if (line.cid === cid) {
                    // with nextpay payment method, we can remove payment line in 'done' status
                    if (['done'].includes(lines[i].get_payment_status())) {
                        line.set_payment_status('waitingCancel');
                        this.render_paymentlines();
                        line.payment_method.payment_terminal.send_payment_cancel(this.pos.get_order(), cid).then(function () {
                            self.pos.get_order().remove_paymentline(line);
                            self.reset_input();
                            self.render_paymentlines();
                        });
                        return;
                    }
                }
            }
            return this._super.apply(this, arguments);
        },

        render_paymentlines: function () {
            let res = this._super.apply(this, arguments);
            let selected_payment_line = this.pos.get_order().selected_paymentline;
            if (selected_payment_line) {
                this.payment_interface = selected_payment_line.payment_method.payment_terminal
            }
            return res;
        },

        render_payment_terminal: function () {
            let self = this;
            var order = this.pos.get_order();
            if (!order) {
                return;
            }
            this._super.apply(this, arguments);
            this.$el.find('.send_payment_request').unbind('click');
            this.$el.find('.send_payment_request').click(function () {
                var cid = $(this).data('cid');
                // Other payment lines can not be reversed anymore
                order.get_paymentlines().forEach(function (line) {
                    line.can_be_reversed = false;
                });

                var line = self.pos.get_order().get_paymentline(cid);
                var payment_terminal = line.payment_method.payment_terminal;
                line.set_payment_status('waiting');
                self.render_paymentlines();

                payment_terminal.send_payment_request(cid).then(function (payment_response) {
                    let payment_terminal = line.payment_method.payment_terminal.payment_method.use_payment_terminal;
                    if (['vnpay', 'nextpay'].includes(payment_terminal)) {
                        let status = payment_response.status;
                        line.set_payment_status(status);
                    } else {
                        if (payment_response) {
                            line.set_payment_status('done');
                            line.can_be_reversed = self.payment_interface.supports_reversals;
                            self.reset_input(); // in case somebody entered a tip the amount tendered should be updated
                        } else {
                            // waiting cashier process payment transaction and we will update status of this payment
                            // after we received response from payment provider
                            line.set_payment_status('waitingCard');
                        }
                    }

                }).finally(function () {
                    self.render_paymentlines();
                });

                self.render_paymentlines();
            });
            this.$el.find('.force_payment_done_manually').click(function () {
                let cid = $(this).data('cid');
                let line = self.pos.get_order().get_paymentline(cid);
                line.transaction_id = 'done_manually';
                line.set_payment_status('done');
                self.render_paymentlines();
            })
            this.$el.find('.force_return_payment_done_manually').click(function () {
                let cid = $(this).data('cid');
                let order = self.pos.get_order();
                let return_order_ref = order.return_order_ref;
                let return_order = self.pos.db.get_order_by_id[return_order_ref];
                let line = order.get_paymentline(cid);
                let line_payment_method_id = line.payment_method.id;
                if (line.amount < 0 && return_order) {
                    let err_message = '';
                    if (!return_order.payment_ids.includes(line_payment_method_id)) {
                        err_message = _.str.sprintf(_t("You can't process this payment by payment method '%s' for this return order"), line.name);
                    }

                    let current_date = new Date().getDate();
                    let return_order_date = parseInt(return_order.date_order.split('/')[0]);
                    if (current_date !== return_order_date) {
                        err_message = _t("You can't process this payment because the return order date is different with current date")
                    }
                    if (err_message) {
                        self.gui.show_popup('error', {
                            'title': _t('Error'),
                            'body': err_message,
                        });
                        return;
                    }
                }
                line.transaction_id = 'return_done_manually';
                line.set_payment_status('done');
                self.render_paymentlines();
            })
        },

        payment_input: function (input) {
            let paymentline = this.pos.get_order().selected_paymentline;
            if (!paymentline) return;
            return this._super.apply(this, arguments);
        },

    })
})