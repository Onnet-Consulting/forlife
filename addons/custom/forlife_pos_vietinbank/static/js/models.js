odoo.define('forlife_pos_vietinbank.models', function (require) {
    const {Order} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');
    const utils = require('web.utils');
    const round_pr = utils.round_precision;


    const PosVietinbankModel = (Order) =>
        class PosVietinbankModel extends Order {
            /* ---- Payment Lines --- */
            add_paymentline(payment_method) {
                const newPaymentline = super.add_paymentline(payment_method);
                if (payment_method.use_payment_terminal === "vietinbank" && newPaymentline) {
                    newPaymentline.set_payment_status('get_transaction_from_vietinbank');
                }
                return newPaymentline;
            }

            get_due(paymentline) {
                const due = super.get_due(...arguments)
                if (this.is_vietinbank() &&  due <= 0) {
                    this.selected_paymentline.set_payment_status('done')
                }
                return due
            }

            is_vietinbank() {
                return this.selected_paymentline && this.selected_paymentline.payment_method.use_payment_terminal === 'vietinbank'
            }

            get_total_paid() {
                const self = this
                return round_pr(this.paymentlines.reduce((function (sum, paymentLine) {
                    if (paymentLine.is_done() || self.is_vietinbank()) {
                        sum += paymentLine.get_amount();
                    }
                    return sum;
                }), 0), this.pos.currency.rounding);
            }
        }

    Registries.Model.extend(Order, PosVietinbankModel);
});