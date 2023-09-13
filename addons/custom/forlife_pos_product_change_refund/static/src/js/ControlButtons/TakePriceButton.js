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
            let selected_line = this.env.pos.get_order().get_orderlines().find(l=>l.is_selected());
            var products_in_cart = [selected_line.product.id];
            return rpc.query({
                model: 'product.defective',
                method: 'get_product_defective',
                args: [this.env.pos.config.store_id[0], products_in_cart, this.env.pos.config.store_id[1]],
            });
        }

        _check_can_be_apply_defective_discount(line) {
            if (line.promotion_usage_ids.length && line.promotion_usage_ids.some(u=>u.promotion_type != 'pricelist')) {
                return false;
            };
            if (line.discount) return false;
            if (line.point) return false;
            if (line.card_rank_discount) return false;
            if (line.refunded_orderline_id) return false;
            if (line.product_defective_id) return false;
            return true;
        };

        async onClick() {
            let selected_line = this.env.pos.get_order().get_orderlines().find(l=>l.is_selected());
            if (!selected_line){
                this.showPopup('ErrorPopup', {
                    title: this.env._t("Warning"),
                    body: _.str.sprintf(this.env._t("Vui lòng chọn một sản phẩm để kiểm tra giá hàng lỗi !"), ''),
                });
                return;
            }
            if (!this._check_can_be_apply_defective_discount(selected_line)) {
                this.showPopup('ErrorPopup', {
                    title: this.env._t("Warning"),
                    body: _.str.sprintf(this.env._t("Sản phẩm đã được áp dụng chương trình khuyến mãi khác. \n Vui lòng đặt lại CTKM trước khi kiểm tra giá hàng lỗi !"), ''),
                });
                return;
            };
            var line_product_defective;
            var product_defective_id;
            if(!this.env.pos.selectedOrder.product_defective_id){
                product_defective_id = false
            }else{
                product_defective_id = this.env.pos.selectedOrder.product_defective_id
            }

            var response = await this.getProductDefective();
            if (!response.length) {
                this.showPopup('ErrorPopup', {
                    title: this.env._t("Warning"),
                    body: _.str.sprintf(this.env._t("Không có CT giảm giá hàng lỗi cho sản phẩm đang chọn!")),
                });
                return;
            };
            this.env.pos.selectedOrder.responseOfproductDefective = response;
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