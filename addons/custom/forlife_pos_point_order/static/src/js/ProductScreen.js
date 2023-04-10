odoo.define('forlife_pos_point_order.ProductScreen', function (require) {
    "use strict";

    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');
    const rpc = require('web.rpc');

    const PointProductScreen = ProductScreen => class extends ProductScreen {

        get_partner_point(id) {
            return rpc.query({
                model: 'pos.session',
                method: 'loader_data_res_partner_from_ui',
                args: [[id]],
            });
        }

        reassign_point(){
                for(var i =0; i< this.currentOrder.orderlines.length; i++){
                    this.currentOrder.orderlines[i].point = 0
                }
                this.currentOrder.total_order_line_point_used = 0
                this.currentOrder.total_order_line_redisual = 0
        }

        async onClickPartner() {
            // IMPROVEMENT: This code snippet is very similar to selectPartner of PaymentScreen.
            const currentPartner = this.currentOrder.get_partner();
            if (currentPartner && this.currentOrder.getHasRefundLines()) {
                this.showPopup('ErrorPopup', {
                    title: this.env._t("Can't change customer"),
                    body: _.str.sprintf(
                        this.env._t(
                            "This order already has refund lines for %s. We can't change the customer associated to it. Create a new order for the new customer."
                        ),
                        currentPartner.name
                    ),
                });
                return;
            }
            const { confirmed, payload: newPartner } = await this.showTempScreen(
                'PartnerListScreen',
                { partner: currentPartner }
            );
            if (newPartner){
                var id = newPartner.id
                var partner_rpc = await this.get_partner_point(id)
                newPartner.total_points_available_format = partner_rpc.total_points_available_format
                newPartner.total_points_available_forlife = partner_rpc.total_points_available_forlife
                this.reassign_point()
            }
            if (confirmed) {
                this.currentOrder.set_partner(newPartner);
                this.currentOrder.updatePricelist(newPartner);
                this.reassign_point()
            }
        }



    };

    Registries.Component.extend(ProductScreen, PointProductScreen);

    return ProductScreen;

});