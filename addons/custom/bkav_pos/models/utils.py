import random
import string
from datetime import date, datetime, timedelta

def genarate_code(self, model, default_code=None):
    code = '982' 
    if not default_code:
        param_code = code+'%'
        query = """ 
            SELECT code
            FROM (
                (SELECT '0000000' as code)
                UNION ALL
                (SELECT RIGHT(code,7) as code
                FROM {table}
                WHERE code like %(param_code)s
                ORDER BY code desc
                LIMIT 1)) as compu
            ORDER BY code desc LIMIT 1
        """.format(table=model._table)
        self._cr.execute(query, {'param_code': param_code})
        result = self._cr.fetchall()
        list_code = result[0]
        if list_code[0] == '0000000':
            code+='0000001'
        else:
            code_int = int(list_code[0])
            code +='0'*(7-len(str(code_int+1)))+str(code_int+1)
        return code
    else:
        list_code = default_code.replace(code, '')
        code_int = int(list_code)
        code +='0'*(7-len(str(code_int+1)))+str(code_int+1)
        return code

def create_move_line(self, line, lines_store={}, product_line_rel={}):
    product_id = line.product_id.id
    pk = f"{line.product_id.barcode}_{float(line.price_unit)}"
    if lines_store.get(pk):
        item = lines_store[pk]
        invoice_ids = item["invoice_ids"]
        invoice_ids.append(line.order_id.id)
        item["quantity"] += line.qty
        item["invoice_ids"] = list(set(invoice_ids))
    else:
        lines_store[pk] = {
            "product_id": product_id,
            "quantity": line.qty,
            "price_unit": line.price_bkav,
            "invoice_ids": [line.order_id.id]
        }

    # if line.product_id:
    #     product_id = line.product_id.id
    #     row = {line.id: line}

    #     if product_line_rel.get(product_id):
    #         old_row = product_line_rel[product_id]
    #         add_line = True
    #         for k, v in old_row.items():
    #             if v.price_bkav == line.price_bkav:
    #                 add_line = False
    #                 lines_store[k]["quantity"] += v.qty
    #                 invoice_ids = lines_store[k]["invoice_ids"]
    #                 invoice_ids.append(line.order_id.id)
    #                 lines_store[k]["invoice_ids"] = list(set(invoice_ids))
    #                 break
    #         if add_line:
    #             product_line_rel[product_id].update(row)
    #             lines_store[line.id] = {
    #                 "product_id": product_id,
    #                 "quantity": line.qty,
    #                 "price_unit": line.price_bkav,
    #                 "invoice_ids": [line.order_id.id]
    #             }
    #     else:
    #         product_line_rel[product_id] = row
    #         lines_store[line.id] = {
    #             "product_id": product_id,
    #             "quantity": line.qty,
    #             "price_unit": line.price_bkav,
    #             "invoice_ids": [line.order_id.id]
    #         }

        
def compare_move_lines(
    self, 
    items={}, 
    store={}, 
    lines=[], 
    missing_line=[], 
    page=0, 
    first_n=0, 
    last_n=1000,
    code=None,
    model=None
):
    pk = f"{store.id}_{page}"
    lines_store = {}
    product_line_rel = {}
    if len(lines) > last_n:
        # n = last_n - 1
        # if x:= len(missing_line):
        #     n = n - x
        
        # for line in missing_line:
        #     create_move_line(self, line, lines_store, product_line_rel)

        # missing_line = []

        # last_line = lines[n]
        # pre_last_line = lines[n - 1]

        # po_order_id = None
        # if pre_last_line.order_id == last_line.order_id:
        #     po_order_id = last_line.order_id.id

        separate_lines = lines[first_n:last_n]
        del lines[first_n:last_n]

        for line in separate_lines:
            # if po_order_id and line.order_id.id == po_order_id:
            #     missing_line.append(line)
            #     continue
            if not line.product_id.barcode:
                continue
            create_move_line(self, line, lines_store, product_line_rel)

        
        items[pk] = {
            'code': code,
            'company_id': lines[0].company_id.id,
            'store_id': store.id,
            'partner_id': store.contact_id.id,
            'invoice_date': date.today(),
            'line_ids': list(lines_store.values())
        }
        page += 1
        compare_move_lines(
            self, 
            items=items, 
            store=store, 
            lines=lines, 
            missing_line=missing_line, 
            page=page, 
            first_n=first_n, 
            last_n=last_n,
            code=genarate_code(self, model, default_code=code),
            model=model
        )
    else:
        for line in lines:
            if not line.product_id.barcode:
                continue
            create_move_line(
                self,
                line, 
                lines_store, 
                product_line_rel
            )
        items[pk] = {
            'code': code,
            'company_id': lines[0].company_id.id,
            'store_id': store.id,
            'partner_id': store.contact_id.id,
            'invoice_date': date.today(),
            'line_ids': list(lines_store.values())
        }


def collect_pos_to_bkav_end_day(self, lines, model, model_line):
    pos_order = lines.mapped("order_id")
    stores = pos_order.mapped("store_id")
    items = {}
    code = genarate_code(self, model)
    for store in stores:
        lines_store = lines.filtered(lambda r: r.order_id.store_id.id == store.id)
        compare_move_lines(
            self,
            items=items,
            store=store,
            lines=list(lines_store),
            missing_line=[],
            page=0, 
            first_n=0, 
            last_n=1000,
            code=code,
            model=model
        )

    for k, v in items.items():
        res_line = model_line.create(v["line_ids"])
        v["line_ids"] = res_line.ids

    vals_list = list(items.values())

    res = model.create(vals_list)
    return res
