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
                error_continue:[],
                check_error: false,
                data: false,
                valid: true,
                data_old: false
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
            var data = this.state.data;
            if(!data){
                data = this.env.pos.selectedOrder.data_voucher;
            };
            if(!data) return;
            var self = this;
            var check_error = this.state.check_error
            $('.o_table_error').each(function( index ) {
                  if($(this).text()){
                      check_error = true
                  }
            })
            if(this.state.valid == true && check_error == false && data != false){
                 $('.o_price_used').each(function( index ) {
                    if(data[index].value != false){
                        let price_used = $(this).val()
                        data[index].value.price_used = parseInt(price_used.split('.').join('').replace('₫',''))
                        delete data[index].value.price_change
                        delete data[index].value.price_residual
                        delete data[index].value.end_date_not_format
                        delete data[index].value.product_apply_ids
                        delete data[index].value.is_full_price_applies
                        delete data[index].value.has_condition
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
                 this.env.pos.selectedOrder.data_voucher = data;

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

        cancel(){
            this.env.posbus.trigger('close-popup', {
                    popupId: this.props.id,
                    response: {confirmed: false, payload: false},
            });
        }

        _deleteValue(ev){
//            this._onValueChange()
            var self = this;
            var data = this.state.data;
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
            var id = parseInt(ev.currentTarget.id)
            for(let i = 0; i< data.length; i++){
                if(i == id){
                    data[i].value = false;
                }
            }
            for(let i = 0; i< this.env.pos.selectedOrder.data_voucher.length; i++){
                if(i == id){
                    this.env.pos.selectedOrder.data_voucher[i].value = false;
                }
            }

        }

        _onValueChange() {
            var self = this;
            self.state.valid = true;
            if(this.env.pos.selectedOrder.data_voucher != false){
                    $('.o_price_used').each(function( index ){
                        if(self.env.pos.selectedOrder.data_voucher[index].value !== false){
                            let price_used = $(this).val()
                            let price_used_convert = parseInt(price_used.split('.').join('').replace('₫',''))
                            if(price_used_convert > parseInt(self.env.pos.selectedOrder.data_voucher[index].value.price_residual_no_compute)){
                                self.state.valid = false;
                                self.env.pos.selectedOrder.data_voucher[index].value.price_used = price_used_convert
                                $(this).css('color', 'red');
                            }
                            if(price_used_convert <= parseInt(self.env.pos.selectedOrder.data_voucher[index].value.price_residual_no_compute)){
                                self.env.pos.selectedOrder.data_voucher[index].value.price_used = price_used_convert
                                $(this).css('color', '#444');
                            }
                        }
                })
            }
            this.state.data = this.env.pos.selectedOrder.data_voucher;
        }

        async check() {
            this.state.data = false;
            this.state.trigger = false;
            this.state.error = [];
            this.state.error_continue = [];
            var self = this;
            var codes = []
            $('.o_price_used').each(function( index ){
                 $(this).css('color', '#444')
            });
            $('.o_input_code').each(function( index ) {
                if($(this).val()){
                    codes.push({
                        value: $.trim($(this).val()).toUpperCase()
                    })
                }else{
                    codes.push({
                        value: false
                    })
                }

            });
            var pos_brand = false;
            for(let i=0; i<this.env.pos.pos_branch.length; i++){
                pos_brand = this.env.pos.pos_branch[i].id
            };
            var data = await this.check_voucher(codes);
            $('.o_input_priority').each(function(index) {
                $(this).val('')
                if(data[index].value != false){
                   $(this).val(index+1)
                }
            });
            var total_price_residual=0
            var total_price_order_line = 0;
            var data_value = []
            for(let i = 0; i < data.length; i ++){
                if(codes[i].value != false && data[i].value != false){
                    total_price_residual+= data[i].value.price_residual
                    data_value.push(data[i].value)
                    if(data[i].value.price_change == 0){
                        data[i].value.price_change = data[i].value.price_residual
                    }
                }
            }

//            validate error expect
            var priority = []
            for(let i = 0; i < data.length; i ++){
                let error = [];
                let error_continue = [];
                if(codes[i].value != false && data[i].value == false){
                    error.push("Không tìm thấy mã voucher hợp lệ!")
                }
                if(codes[i].value != false && data[i].value != false){
                        let pri = i+1;
                        priority.push(pri)
                        if(data[i].value.brand_id != pos_brand){
                            error.push("Không trùng khớp mã thương hiệu!")
                        }
                        if(data[i].value.partner != false && data[i].value.partner != this.env.pos.selectedOrder.partner.id){
                            error.push("Không trùng khớp mã khách hàng!")
                        }
                        if(data[i].value.store_ids.length > 0 && data[i].value.store_ids.includes(this.env.pos.config.store_id[0]) == false){
                            error.push("Không trùng khớp mã cửa hàng!")
                        }
                        if(data[i].value.state == 'new'){
                            error.push("Mã voucher chưa được sử dụng!")
                        }
                        if(data[i].value.state == 'off value'){
                            error.push("Mã voucher đã hết giá trị sử dụng!")
                        }
                        if(data[i].value.state == 'expired'){
                            error.push("Mã voucher đã hết thời gian sử dụng!")
                        }
                        if(!data[i].value.apply_contemp_time && data_value.length > 1){
                            error.push("Voucher chỉ được sử dụng độc lập!")
                        }
                        if(this.env.pos.selectedOrder.creation_date < new Date(data[i].value.start_date)){
                            error.push("Mã voucher chưa đến thời gian sử dụng!")
                        }
                        let check_product = false;
                        for(let j = 0; j< this.env.pos.selectedOrder.orderlines.length; j++){
                            if(data[i].value.product_apply_ids.length > 0 && data[i].value.product_apply_ids.includes(this.env.pos.selectedOrder.orderlines[j].product.product_tmpl_id) == true){
                                if(data[i].value.is_full_price_applies == true && 'point' in this.env.pos.selectedOrder.orderlines[j] && this.env.pos.selectedOrder.orderlines[j].point){
                                    error_continue.push("Sản phẩm "+ this.env.pos.selectedOrder.orderlines[j].product.display_name +" nếu muốn sử dụng voucher sẽ cần được xóa chương trình khuyến mại trên giỏ hàng!")
                                }
                                check_product = true
                            }else if(data[i].value.product_apply_ids.length == 0){
                                check_product = true
                            }
                        }
                        if(check_product == false){
                            error.push("Sản phẩm được áp dụng voucher không có trong giỏ hàng!")
                        }
                        if(this.env.pos.selectedOrder.creation_date > new Date(data[i].value.end_date_not_format)){
                            error.push("Mã voucher đã hết thời gian sử dụng!")
                        }
                }
                this.state.error.push(error)
                this.state.error_continue.push(error_continue)
            }
//            validate price fill
            for(let i = 0; i < data.length; i ++){
                if(data[i].value != false){
                   if(data[i].value.product_apply_ids.length == 0){
                        data[i].value.has_condition = false;
                   }
                   if(data[i].value.product_apply_ids.length > 0){
                        data[i].value.has_condition = true;
                   }
                }
            }
            var so_tien_da_tra = {};
            var gia_tri_con_lai_ban_dau =0;
            var total_dua = this.env.pos.selectedOrder.get_due();
            var price_dua = 0;
            var list_id_product_apply_condition = []
            for(let i = 0; i < data.length; i ++){
                if(codes[i].value != false && data[i].value != false){
                   gia_tri_con_lai_ban_dau = data[i].value.price_residual
                   this.env.pos.selectedOrder.orderlines.forEach(function(item){
                        if((!data[i].value.has_condition || data[i].value.product_apply_ids.includes(item.product.product_tmpl_id)) && !(item.point && data[i].value.is_full_price_applies)){
                            let item_id = item.id.toString()
                            if(!so_tien_da_tra[item_id]){
                                so_tien_da_tra[item_id] = 0;
                            }
                            if(!item.point){
                                item.point = 0
                            }
                            if(data[i].value.price_residual >= (item.product.lst_price*item.quantity + item.point - so_tien_da_tra[item_id])){
                                data[i].value.price_residual = data[i].value.price_residual-(item.product.lst_price*item.quantity - so_tien_da_tra[item_id] + item.point);
                                so_tien_da_tra[item_id] = item.product.lst_price*item.quantity + item.point;
                            }else{
                                so_tien_da_tra[item_id] = so_tien_da_tra[item_id] + data[i].value.price_residual;
                                data[i].value.price_residual = 0;
                            }
                            if(data[i].value.product_apply_ids.includes(item.product.product_tmpl_id)){
                                list_id_product_apply_condition.push(item.id)
                            }
                        }
                   })
                data[i].value.price_change = gia_tri_con_lai_ban_dau - data[i].value.price_residual;
               }
            }
            this.env.pos.selectedOrder.orderlines.forEach(function(line){
                let line_id = line.id.toString()
                if(list_id_product_apply_condition.includes(line.id)){
                    line.is_voucher_conditional = true;
                }else{
                    line.is_voucher_conditional = false;
                }
            });

            for(let i=0;i<data.length;i++){
                if(data[i].value != false){
                    data[i].value.price_residual = data[i].value.price_residual + data[i].value.price_change
                }
            }
//            for(let i = 0; i < data.length; i ++){
//                if(codes[i].value != false && data[i].value != false){
//                   this.env.pos.selectedOrder.orderlines.forEach(function(item){
//                        if((!data[i].value.has_condition || data[i].value.product_apply_ids.includes(item.product.product_tmpl_id)) && !(item.point && data[i].value.is_full_price_applies)){
//                            if(data[i].value.price_residual >= total_dua){
//                                data[i].value.price_residual = total_dua
//                            }
//                        }
//                   })
//               }
//            }
            this.state.data = data;
            this.state.data_old = data;
            for(let i=0;i<this.state.data_old.length;i++){
                if(this.state.data_old[i].value != false){
                    this.state.data_old[i].value.priority = i+1
                }
            }
            this.env.pos.selectedOrder.data_voucher = false;
        }
    }

    VoucherPopup.template = "VoucherPopup";
    VoucherPopup.defaultProps = {
        title: _t("Voucher")
    };
    Registries.Component.add(VoucherPopup);

    return VoucherPopup;
})