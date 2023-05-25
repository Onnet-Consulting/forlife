odoo.define('forlife_point_of_sale.PaymentScreen', function(require) {
    "use strict";

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');


    const CustomPaymentScreen = PaymentScreen => class extends PaymentScreen {

        onInputInvoiceInfo(target) {
            let field = target.name;
            let value = target.value;
            if (['invoice_info_company_name', 'invoice_info_address', 'invoice_info_tax_number'].includes(field)) {
                let order = this.env.pos.get_order();
                order[field] = value;
            };
        }
    };

    Registries.Component.extend(PaymentScreen, CustomPaymentScreen);

    return PaymentScreen;
});
