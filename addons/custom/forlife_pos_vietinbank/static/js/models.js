odoo.define('forlife_pos_vietinbank.models', function (require) {
    const {Order} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');

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
        }

    Registries.Model.extend(Order, PosVietinbankModel);
});