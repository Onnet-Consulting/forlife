odoo.define('forlife_pos_payment_terminal.models', function (require) {
    let models = require('point_of_sale.models');
    let PaymentNextPay = require('forlife_pos_payment_terminal.payment_nextpay');
    let PaymentVNPay = require('forlife_pos_payment_terminal.payment_vnpay');

    models.load_fields("pos.payment.method", ["vnpay_type"]);

    models.register_payment_method('nextpay', PaymentNextPay);
    models.register_payment_method('vnpay', PaymentVNPay);

    let _super_PaymentLine = models.Paymentline.prototype;
    models.Paymentline = models.Paymentline.extend({
        initialize: function (attributes, options) {
            _super_PaymentLine.initialize.call(this, attributes, options);
            // use this to determine transaction id on payment terminal
            this.unique_id = this.unique_id || `${this.pos.config.id}_${(+new Date()).toString()}`;
        },

        init_from_JSON: function (json) {
            this.unique_id = json.unique_id;
            _super_PaymentLine.init_from_JSON.apply(this, arguments);
        },

        export_as_JSON: function () {
            let res = _super_PaymentLine.export_as_JSON.apply(this, arguments);
            res.unique_id = this.unique_id;
            return res;
        },
    })

    let _super_PosModel = models.PosModel;
    models.PosModel = models.PosModel.extend({
        initialize: function () {
            _super_PosModel.prototype.initialize.apply(this, arguments);
            let self = this;
            this.ready.then(function () {
                self.bus.add_channel_callback(
                    "vnpay_transaction_sync",
                    self.on_vnpay_payment_transaction_update,
                    self
                );
                self.bus.add_channel_callback(
                    "nextpay_transaction_sync",
                    self.on_nextpay_payment_transaction_update,
                    self
                );
            });
        },
        on_vnpay_payment_transaction_update: function (data) {
            let self = this;
            let order = this.get_order();
            if (!this.gui) return false;
            let payment_screen = this.gui.screen_instances.payment

            let selected_payment_line = order.get_paymentlines().filter((line) => {
                let payment_transaction_id = line.unique_id;
                return payment_transaction_id === data.clientTransactionCode;
            })
            if (selected_payment_line.length > 0) {
                let response_code = data.responseCode;
                selected_payment_line = selected_payment_line[0];
                if (response_code === '200') {
                    selected_payment_line.set_payment_status('done');
                    selected_payment_line.transaction_id = data.transactionCode;
                    selected_payment_line.card_type = data.bankCode || '';
                    self.gui.close_popup();
                    payment_screen.render_paymentlines();
                } else {
                    selected_payment_line.payment_method.payment_terminal._show_error(data.responseMessage);
                    selected_payment_line.set_payment_status('retry');
                }
            }
        },
        on_nextpay_payment_transaction_update: function (data) {
            let self = this;
            let order = this.get_order();
            if (!this.gui) return false;
            let payment_screen = this.gui.screen_instances.payment

            let selected_payment_line = order.get_paymentlines().filter((line) => {
                let payment_transaction_id = line.unique_id;
                return payment_transaction_id === data.orderId;
            })

            if (selected_payment_line.length > 0) {
                selected_payment_line = selected_payment_line[0];
                let transaction_code = data.transStatus;
                if (transaction_code === 100) {
                    selected_payment_line.set_payment_status('done');
                    selected_payment_line.transaction_id = data.orderId;
                    selected_payment_line.card_type = data.issuerCode || '';
                    payment_screen.render_paymentlines();
                } else {
                    selected_payment_line.payment_method.payment_terminal._show_error("Something went wrong, please re-check on NextPay");
                    selected_payment_line.set_payment_status('retry');
                }
            }
        },
    })
});