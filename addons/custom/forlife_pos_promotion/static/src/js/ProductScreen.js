/** @odoo-module **/

import ProductScreen from 'point_of_sale.ProductScreen';
import Registries from 'point_of_sale.Registries';
import { useBarcodeReader } from 'point_of_sale.custom_hooks';
import { Gui } from 'point_of_sale.Gui';
import core from 'web.core';
const _t = core._t;

export const PosPromotionProductScreen = (ProductScreen) =>
    class extends ProductScreen {
        async _onClickPay() {
            // Kiểm tra và áp dụng CT Quà tặng bất ngờ
            const order = this.env.pos.get_order();
            // Không áp dụng cho đơn hàng đổi trả
            if (!(order.is_refund_product || order.is_change_product)) {
                order.surprise_reward_program_id = null;
                order.surprise_reward_program_id = null;
                order.surprising_reward_line_id = null;
                let {validSurprisingPrograms, validBuyVoucherGetCodePrograms} = order.verifySurprisingProgram();
                if ((validSurprisingPrograms.length > 0 || validBuyVoucherGetCodePrograms.length > 0) && order.get_partner()) {
                    const { confirmed, payload } = await this.showPopup('SurpriseRewardPopup', {
                        title: this.env._t('Please select some rewards'),
                        validSurprisingPrograms: validSurprisingPrograms || [],
                        validBuyVoucherGetCodePrograms: validBuyVoucherGetCodePrograms || []
                    });
                    let [surprisingReward, buyVoucherRewards] = payload || [];
                    if (surprisingReward) {
                        order.surprise_reward_program_id = surprisingReward.program_id;
                        order.surprising_reward_line_id = surprisingReward.line_id;
                    };
                    if (!_.isEmpty(buyVoucherRewards)) {
                        order.buy_voucher_get_code_rewards = buyVoucherRewards.map(r=> {
                            return {buy_voucher_reward_program_id: r.program_id, surprising_reward_line_id: r.line_id}
                        });
                    };
                };
            };
            // Kiểm tra còn CTKM chưa được áp dụng hết trên đơn
            let applicablePrograms = this.env.pos.get_order().getPotentialProgramsToSelect();
            if (applicablePrograms.length > 0) {
                Gui.showNotification(_.str.sprintf(`Còn chương trình khuyến mãi có thể áp dụng trên đơn hàng này!`), 5000);
            };
            // Kiểm tra đơn hàng sử dụng CTKM bị giới hạn
            await order.get_history_program_usages()
            let invalidProgram = order._validateLimitUsagePromotion();
            if (invalidProgram) {
                let msg = '';
                if (invalidProgram[1] == 'limit_usage_per_order') {
                    msg = `Chỉ ${invalidProgram[1]} combo / 1 đơn hàng`
                } else {
                    let unit = invalidProgram[0].promotion_type == 'code' ? 'lần' : 'combo';
                    msg = `Khả dụng: ${invalidProgram[2]} ${unit}`
                };
                this.showPopup('ErrorPopup', {
                    title: this.env._t('Limited Promotion Validation Error'),
                    body: this.env._t(`Đã vượt quá giới hạn áp dụng của CTKM: ${invalidProgram[0].display_name}. ${msg}`),
                });
            } else {
                return super._onClickPay(...arguments);
            };
        }

        _setNumpadMode(event) {
            const {mode} = event.detail;
            if (mode == 'discount') {
                let selected_orderline = this.currentOrder.get_selected_orderline();
                if (selected_orderline &&
                    (  selected_orderline.is_applied_promotion()
                    || selected_orderline.card_rank_applied
                    || selected_orderline.is_product_defective
                    || selected_orderline.point
                    || selected_orderline.handle_change_refund_price)) {
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Lỗi thao tác'),
                        body: this.env._t('Bạn cần loại bỏ CTKM trước khi áp dụng chiết khấu tay!'),
                    });
                    return false;
                };
            };
            return super._setNumpadMode(...arguments);
        }
    };

Registries.Component.extend(ProductScreen, PosPromotionProductScreen);
