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