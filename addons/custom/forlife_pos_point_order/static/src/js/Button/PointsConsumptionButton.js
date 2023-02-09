odoo.define('forlife_pos_point_order.PointsConsumptionButton', function (require) {
    "use strict";


    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');
    const {useListener} = require("@web/core/utils/hooks");
    const rpc = require('web.rpc');


    class PointsConsumptionButton extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.onClick);
        }

        get promotion () {
            var self = this;
            let data = {
                'session_id': self.env.pos.pos_session.id,
                'date_order': self.env.pos.selectedOrder.creation_date,
            }
            return rpc.query({
                model: 'pos.order',
                method: 'get_program_promotion',
                args: [data],
                context: {
                     from_PointsConsumptionPos :true
                }
            });
        }

        get order_lines(){
            return this.env.pos.get_order().get_orderlines();
        }

        async onClick() {
            if(!this.env.pos.selectedOrder.partner){
                console.log('Chưa chọn khách hàng cho đơn này');
                return;
            }
            if (this.env.pos.pos_branch) {
                console.log(true);
            } else {
                console.log('Chưa thiết lập chi nhánh cho POS này');
                return;
            }
            var points_of_customer = null;
            for (let index = 0; index < this.env.pos.pos_branch.length; index++) {
                if(this.env.pos.pos_branch[index].name == "Format"){
                    points_of_customer = this.env.pos.selectedOrder.partner.total_points_available_format
                }else {
                    points_of_customer = this.env.pos.selectedOrder.partner.total_points_available_forlife
                }
            }
            var order_lines = this.order_lines;
            var promotion = await this.promotion;
            var product_valid = []
//                các sản phẩm hợp lệ được cấu hình
            for (let i=0; i< order_lines.length;i++){
                    for(let j=0;j<promotion.point_consumption_ids.length;j++){
                        if(order_lines[i].product.id == promotion.point_consumption_ids[j].id){
                            product_valid.push(order_lines[i]);
                        }
                    }
                }

            const {confirmed, payload: data} = await this.showPopup('PointsConsumptionPopup', {
                startingValue: this.order_lines,
                orderlines:this.env.pos.selectedOrder.orderlines,
                points_of_customer: points_of_customer,
                program_promotion: promotion,
                product_valid: product_valid,
                title: this.env._t('Tiêu điểm'),
                confirmTitle: this.env._t('Xác nhận '),
                divisionpoint: this.env._t('Chia điểm'),
                cancelTitle: this.env._t('Xóa')
            });

            if(confirmed){
                console.log('333')
            }
        }

    }

    PointsConsumptionButton.template = 'PointsConsumptionButton';

    ProductScreen.addControlButton({
        component: PointsConsumptionButton,
        condition: function () {
            return this.env.pos;
        },
    })

    Registries.Component.add(PointsConsumptionButton);

    return PointsConsumptionButton;
})