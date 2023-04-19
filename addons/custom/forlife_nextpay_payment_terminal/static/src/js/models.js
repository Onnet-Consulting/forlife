odoo.define('forlife_nextpay_payment_terminal.models', function (require) {
    const models = require('point_of_sale.models');
    const {Payment} = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');
    const PaymentNextPay = require('forlife_nextpay_payment_terminal.payment');

    const PosNextPayPayment = (Payment) => class PosNextPayPayment extends Payment {
        constructor(obj, options) {
            super(obj, options);
            this.unique_id = this.unique_id || `${this.pos.config.id}_${(+new Date()).toString()}`;
        }

        init_from_JSON(json) {
            super.init_from_JSON(...arguments);
            this.unique_id = json.unique_id;
        }

        export_as_JSON() {
            return _.extend(super.export_as_JSON(...arguments), {
                unique_id: this.unique_id
            });
        }
    }

    Registries.Model.extend(Payment, PosNextPayPayment);

    models.register_payment_method('nextpay', PaymentNextPay);
});
