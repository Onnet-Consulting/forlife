odoo.define('forlife_pos_assign_employee.ProductScreen', function (require) {
    "use strict";

    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');
    const ReceiptScreen = require('point_of_sale.ReceiptScreen');

    const EmployeeProductScreen = ProductScreen => class extends ProductScreen {
        async _onClickPay() {
            if (this.currentOrder.get_orderlines().length === 0) {
                this.showPopup('ErrorPopup', {
                    title: this.env._t('Empty Order'),
                    body: this.env._t(
                        'There must be at least one product in your order before it can be process payment.'
                    ),
                });
                return false;
            }
            if (!this.currentOrder.get_partner()) {
                this.showPopup('ErrorPopup', {
                    title: this.env._t('Empty Order'),
                    body: this.env._t(
                        'Hãy chọn một khách hàng!'
                    ),
                });
                return false;
            }
            if (this.currentOrder.get_orderlines().some(line => !line.employee_id)) {
                this.showPopup('ErrorPopup', {
                    title: this.env._t('Missing employee'),
                    body: this.env._t(
                        'Please assign employee for all order lines'
                    ),
                });
                return false;
            }
            return await super._onClickPay(...arguments);
        }
    };

    const ReceiptScreenExtend = ReceiptScreen => class extends ReceiptScreen {
        orderDone() {
            super.orderDone();
            this.env.pos.employeeSelected.employeeID = null;
        }
    }

    Registries.Component.extend(ProductScreen, EmployeeProductScreen);
    Registries.Component.extend(ReceiptScreen, ReceiptScreenExtend);

    return ProductScreen;

});