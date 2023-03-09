odoo.define('forlife_voucher.VoucherPopup', function (require) {
    "use strict";

    let core = require('web.core');
    let _t = core._t;

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {onMounted, useRef, useState} = owl;
    const {useBus} = require('@web/core/utils/hooks');
    const rpc = require('web.rpc');

    class VoucherPopup extends AbstractAwaitablePopup {
        setup() {
            super.setup();
            this.state = useState({
                error: [],
                check_error: false,
                data: false,
                valid: true
            });
        }

        check_voucher(codes) {
            return rpc.query({
                model: 'voucher.voucher',
                method: 'check_voucher',
                args: [codes],
                context: {
                     branch : false
                }
            });
        }



        confirm() {
            var data = this.state.data
            if(this.state.valid == true && this.state.check_error == false && data != false){
                 $('.o_price_used').each(function( index ) {
                    if(data[index].value != false){
                        let price_used = $(this).val()
                        data[index].value.price_used = parseInt(price_used.split('.').join('').replace('₫',''))
                    }
                 });
                 $('.o_input_priority').each(function( index ) {
                    if(data[index].value != false){
                        let priority = $(this).val()
                        data[index].value.priority = parseInt(priority)
                    }
                 });
                 for(let i=0; i< data.length; i++){
                    if(data[i].value != false){
                        this.env.posbus.trigger('close-popup', {
                            popupId: this.props.id,
                            response: {confirmed: true, payload: data},
                        });
                    }
                 }

            }else{
                this.showPopup('ErrorPopup', {
                    title: this.env._t("Warning"),
                    body: _.str.sprintf(
                        this.env._t(
                            "Vui lòng kiểm tra lại thông tin Voucher"
                        ),
                    ),
                });
            }
        }


        _deleteValue(ev){
            var self = this;
            $('.o_table_type').each(function( index ) {
              if(index == ev.currentTarget.id){
                  $(this).text('')
              }
            });
            $('.o_input_priority').each(function( index ) {
              if(index == ev.currentTarget.id){
                  $(this).val('')
              }
            });
            $('.o_input_code').each(function( index ) {
              if(index == ev.currentTarget.id){
                  $(this).val('')
              }
            });
            $('.o_table_end_date').each(function( index ) {
              if(index == ev.currentTarget.id){
                  $(this).text('')
              }
            });
            $('.o_table_error').each(function( index ) {
              if(index == ev.currentTarget.id){
                  $(this).text('')
              }
            });
            $('.o_price_residual').each(function( index ) {
              if(index == ev.currentTarget.id){
                  $(this).val('')
              }
            });
            $('.o_price_used').each(function( index ) {
              if(index == ev.currentTarget.id){
                  $(this).val('')
              }
            });
            self.check()
//
        }

        _onValueChange() {
            var data = this.state.data;
            var self = this;
            if(data != false){
                $('.o_price_residual').each(function( i ){
                        if(data[i].value !== false && self.state.error[i].length == 0){
                            $('.o_price_used').each(function( index ){
                            let price_used = $(this).val()
                            let price_used_convert = parseInt(price_used.split('.').join('').replace('₫',''))
                            if(price_used_convert > data[i].value.price_residual){
                                $(this).css('color', 'red');
                                self.state.valid = false;
                            }
                            if(price_used_convert <= data[i].value.price_residual){
                                $(this).css('color', '#444');
                                self.state.valid = true;
                            }
                        })
                        }

                })
            }
        }

        async check() {
            this.state.error = []
            this.state.check_error = false
            var codes = []
            $('.o_price_used').each(function( index ){
                 $(this).css('color', '#444')
            });
            $('.o_input_code').each(function( index ) {
                if($(this).val()){
                    codes.push({
                        value: $(this).val()
                    })
                }else{
                    codes.push({
                        value: false
                    })
                }

            });
            var pos_brand = false
            for(let i=0; i<this.env.pos.pos_branch.length; i++){
                pos_brand = this.env.pos.pos_branch[i].id
            }
            var data = await this.check_voucher(codes)
            for(let i = 0; i < data.length; i ++){
                let error = [];
                if(codes[i].value != false && data[i].value == false){
                    this.state.check_error = true
                    error.push("Không tìm thấy mã voucher hợp lệ!")
                }
                if(codes[i].value != false && data[i].value != false){
                        if(data[i].value.brand_id != pos_brand){
                            this.state.check_error = true
                            error.push("Không trùng khớp mã thương hiệu!")
                        }
                        if(data[i].value.partner != false && data[i].value.partner != this.env.pos.selectedOrder.partner.id){
                            this.state.check_error = true
                            error.push("Không trùng khớp mã khách hàng!")
                        }
                        if(data[i].value.store_ids.length > 0 && data[i].value.store_ids.includes(this.env.pos.config.store_id[0]) == false){
                            this.state.check_error = true
                            error.push("Không trùng khớp mã cửa hàng!")
                        }
                        if(data[i].value.state == 'new'){
                            this.state.check_error = true
                            error.push("Mã voucher chưa được sử dụng!")
                        }
                        if(data[i].value.state == 'off value'){
                            this.state.check_error = true
                            error.push("Mã voucher đã hết giá trị sử dụng!")
                        }
                        if(data[i].value.state == 'expired'){
                            this.state.check_error = true
                            error.push("Mã voucher đã hết thời gian sử dụng!")
                        }
                        if(!data[i].value.apply_contemp_time){
                            this.state.check_error = true
                            error.push("Voucher chỉ được sử dụng độc lập!")
                        }
                        if(this.env.pos.selectedOrder.creation_date < new Date(data[i].value.start_date)){
                            this.state.check_error = true
                            error.push("Mã voucher chưa đến thời gian sử dụng!")
                        }
                }
                this.state.error.push(error)
            }
            this.state.data = data;
        }
    }

    VoucherPopup.template = "VoucherPopup";
    VoucherPopup.defaultProps = {
        title: _t("Voucher")
    };
    Registries.Component.add(VoucherPopup);

    return VoucherPopup;
})