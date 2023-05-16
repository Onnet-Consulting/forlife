odoo.define('forlife_pos_product_change_refund.TakePriceProductPopup', function (require) {
    "use strict";

    const { _t } = require('web.core');

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {onMounted, useRef, useState} = owl;
    const {useBus} = require('@web/core/utils/hooks');

    class TakePriceProductPopup extends AbstractAwaitablePopup {
        setup() {
            super.setup();
        }

        cancel(){
            this.env.posbus.trigger('close-popup', {
                popupId: this.props.id,
                response: {confirmed: false, payload: false},
            });
        }

        onclickCheckbox(ev){
            $('.o_check').each(function(index) {
              if($(this).attr('value') != ev.currentTarget.value){
                   $(this).prop("checked", false);
              }
            });
        }

        confirm(){
            var product_id_checked;
            var products_defective = this.props.response
            var orderlines = this.env.pos.selectedOrder.orderlines
            $('.o_check').each(function(index) {
                if($(this).is(":checked")){
                   product_id_checked = parseInt($(this).attr('value'))
                }
            });
            for(let i =0; i< orderlines.length; i++){
                for(let j=0; j< products_defective.length; j++){
                    if(product_id_checked == orderlines[i].product.id && products_defective[j].product_id == product_id_checked){
                        if(orderlines[i].quantity > products_defective[j].quantity){
                            this.showPopup('ErrorPopup', {
                                title: this.env._t("Warning"),
                                body: _.str.sprintf(
                                    this.env._t(
                                        "Số luợng sản phẩm trên đơn lớn hơn số luợng sản phẩm đã chọn!"
                                    ),
                                    ''
                                ),
                            });
                            return;
                        }
                        orderlines[i].money_reduce_from_product_defective = parseInt(products_defective[j].total_reduce)*products_defective[j].quantity
                        orderlines[i].is_product_defective = true
                    }
                }
            }
            this.env.posbus.trigger('close-popup', {
                popupId: this.props.id,
                response: {confirmed: false, payload: false},
            });
        }

    }

    TakePriceProductPopup.template = "TakePriceProductPopup";
    TakePriceProductPopup.defaultProps = {
        cancelText: _t("Hủy"),
        confirmText: _t("Đồng ý")
    };
    Registries.Component.add(TakePriceProductPopup);

    return TakePriceProductPopup;
})