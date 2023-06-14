if __name__ == '__main__':
    # module = "forlife_stock"
    # module = "stock_inventory"
    # module = "forlife_stock_report"
    module = "account"
    model = "account.payment"
    # dvkh = True
    access = "1,0,0,0"
    model_name = model.replace(".", "_")
    print("\n")

    print(",(4, ref('forlife_permission_management.group_purchase_group_admin'))")
    print("\n")

    group = "group_purchase_group_admin"
    print("access_%s_%s,access_%s_%s,%s.model_%s,%s,%s" % (model_name, group, model_name, group, module, model_name, group, access))
    group = "group_general_accounting"
    print("access_%s_%s,access_%s_%s,%s.model_%s,%s,%s" % (model_name, group, model_name, group, module, model_name, group, access))
    group = "group_manufacturing_accounting"
    print("access_%s_%s,access_%s_%s,%s.model_%s,%s,%s" % (model_name, group, model_name, group, module, model_name, group, access))
    group = "group_liabilities_accounting"
    print("access_%s_%s,access_%s_%s,%s.model_%s,%s,%s" % (model_name, group, model_name, group, module, model_name, group, access))
    group = "group_business_manager"
    print("access_%s_%s,access_%s_%s,%s.model_%s,%s,%s" % (model_name, group, model_name, group, module, model_name, group, access))
    group = "group_manufacture"
    print("access_%s_%s,access_%s_%s,%s.model_%s,%s,%s" % (model_name, group, model_name, group, module, model_name, group, access))
    group = "group_marketing"
    print("access_%s_%s,access_%s_%s,%s.model_%s,%s,%s" % (model_name, group, model_name, group, module, model_name, group, access))
    group = "group_dvkh_1"
    print("access_%s_%s,access_%s_%s,%s.model_%s,%s,%s" % (model_name, group, model_name, group, module, model_name, group, access))
    group = "group_dvkh_2"
    print("access_%s_%s,access_%s_%s,%s.model_%s,%s,%s" % (model_name, group, model_name, group, module, model_name, group, access))
    group = "group_dvkh_3"
    print("access_%s_%s,access_%s_%s,%s.model_%s,%s,%s" % (model_name, group, model_name, group, module, model_name, group, access))
    group = "group_dvkh_4"
    print("access_%s_%s,access_%s_%s,%s.model_%s,%s,%s" % (model_name, group, model_name, group, module, model_name, group, access))