odoo.define('forlife_pos_product_change_refund.TakePriceProduct', function (require) {
    "use strict";

//    const {PosGlobalState, Orderline, Order} = require('point_of_sale.models');
    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');
    const {useListener} = require("@web/core/utils/hooks");
    const rpc = require('web.rpc');


    class TakePriceProductButton extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.onClick);
        }

        getProductDefective(){
            var products_in_cart = []
            this.env.pos.selectedOrder.orderlines.forEach(function(item){
                products_in_cart.push(item.product.id)
            })
            return rpc.query({
                model: 'product.defective',
                method: 'get_product_defective',
                args: [this.env.pos.config.store_id[0], products_in_cart, this.env.pos.config.store_id[1]],
            });
        }

        async onClick() {
            if(this.env.pos.selectedOrder.orderlines.length ==0){
                this.showPopup('ErrorPopup', {
                    title: this.env._t("Warning"),
                    body: _.str.sprintf(
                        this.env._t(
                            "Chưa chọn sản phẩm nào!"
                        ),
                        ''
                    ),
                });
                return;
            }
            var line_product_defective;
            var product_defective_id;
            if(!this.env.pos.selectedOrder.product_defective_id){
                product_defective_id = false
            }else{
                product_defective_id = this.env.pos.selectedOrder.product_defective_id
            }

            var response = await this.getProductDefective()
            this.env.pos.selectedOrder.responseOfproductDefective = response
            const {confirmed, payload: data} = await this.showPopup('TakePriceProductPopup', {
                response: response,
                line_product_defective:line_product_defective,
                product_defective_id: product_defective_id
            });
        }


    }

    TakePriceProductButton.template = 'TakePriceProductButton';

    ProductScreen.addControlButton({
        component: TakePriceProductButton
    })

    Registries.Component.add(TakePriceProductButton);

    return TakePriceProductButton;
})