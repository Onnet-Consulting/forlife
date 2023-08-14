from odoo import api, fields, models
import json
import base64
from io import StringIO
from io import BytesIO
from odoo.addons.base_import.models.base_import import FILE_TYPE_DICT, _logger
from odoo.tools.misc import clean_context


class ChildBatchImport(models.Model):
    _name = "child.batch.import"
    _description = "Manage sub file and execute import"
    _rec_name = "file_name"
    _order = "parent_batch_import_id,sequence"

    sequence = fields.Integer(string="Sequence", default=1)
    parent_batch_import_id = fields.Many2one(string="Parent Batch", comodel_name="parent.batch.import", ondelete='cascade')
    skip = fields.Integer(string='Skip')
    log = fields.Text(string="Log")
    status = fields.Selection([('draft', 'Draft'), ('processing', 'Processing'), ('done', 'Done'), ('error', 'Error'), ('cancel', 'Cancel')], string='Status', default='draft')
    complete_records = fields.Integer(string="Complete Records")
    error_rows = fields.Text(string="Error Rows")
    progress_bar = fields.Float('Progress Done (%)', digits=(16, 2), compute='_compute_progress_bar')
    # binary file
    file = fields.Binary('File', help="File to check and/or import", attachment=True)
    file_name = fields.Char('File Name')
    file_type = fields.Char('File Type')
    file_length = fields.Integer(string="File Length")
    file_invalid_records = fields.Binary(string="Invalid Records", attachment=True)
    file_record_done_from_rule = fields.Binary(string="File record valid", attachment=True)
    file_record_done_from_rule_name = fields.Char('File record valid')
    file_invalid_records_name = fields.Char('Invalid records file')

    def rec_file_csv(self, file):
        import pandas as pd
        self.ensure_one()
        # Giải mã nội dung của attachment
        decoded_data = base64.b64decode(file)
        # Chuyển decoded_data thành đối tượng StringIO để đọc dữ liệu CSV
        file_data = StringIO(decoded_data.decode('utf-8'))
        # Đọc dữ liệu CSV vào DataFrame
        df = pd.read_csv(file_data, dtype=str)
        return df

    def rec_file_exel(self, file):
        import pandas as pd
        self.ensure_one()
        # Giải mã nội dung của attachment
        decoded_data = base64.b64decode(file)

        # Đọc dữ liệu của attachment vào DataFrame với Pandas
        df = pd.read_excel(BytesIO(decoded_data), dtype=str)
        return df

    @api.depends('complete_records', 'file_length')
    def _compute_progress_bar(self):
        for rec in self:
            complete = 0
            if rec.complete_records and rec.file_length > 0:
                complete = (rec.complete_records / int(rec.file_length)) * 100
            rec.progress_bar = complete

    def make_queue_test_batch(self, delay_time=0):
        index = 1
        for rec in self:
            # tạo job queue theo sequence và delay time
            result = rec.with_delay(priority=rec.sequence, eta=delay_time * index).test_execute_import()
            index = index + 1

    def make_queue_job(self, delay_time=0):
        for rec in self:
            # tạo job queue theo sequence và delay time
            result = rec.with_delay(channel='import', priority=rec.sequence, eta=delay_time).batch_execute_import()

    def batch_execute_import(self):
        for rec in self:
            try:
                if rec.file:
                    base_import_from_batch = self.with_context(clean_context(json.loads(rec.parent_batch_import_id.context))).env['base_import.import'].create({
                        'file': base64.b64decode(rec.file),
                        'file_name': rec.file_name,
                        'file_type': rec.file_type,
                        'res_model': rec.parent_batch_import_id.res_model,
                    })
                    # trong trường hợp không phải là file nhỏ đầu tiên, thì sẽ không có has_headers
                    options = json.loads(rec.parent_batch_import_id.options)
                    # if options.get('has_headers') and rec.sequence > 0:
                    #     options['has_headers'] = False
                    fields = json.loads(rec.parent_batch_import_id.list_field)
                    columns = json.loads(rec.parent_batch_import_id.columns)
                    # execute dựa vào hàm base của base_import.import
                    result = base_import_from_batch.execute_import(fields=fields, columns=columns,
                                                                   options=options,
                                                                   dryrun=rec.parent_batch_import_id.dryrun)
                    if result.get('ids') and len(result.get('messages')) == 0:
                        rec.write({
                            'status': 'done',
                            'log': json.dumps(result, ensure_ascii=False),

                        })

                    else:
                        rec.status = 'error'
                        rec.log = json.dumps(result, ensure_ascii=False)
                    index_for_header = 2 if options.get('has_headers') else 1
                    error_rows = []
                    if result.get('messages'):
                        for message in result.get('messages'):
                            if message.get('record'):
                                if message.get('record') not in error_rows:
                                    error_rows.append(message.get('record'))
                    file_length = result.get('file_length') if result.get('file_length') else rec.parent_batch_import_id.limit
                    if len(error_rows) > 0:
                        complete_records = 0
                        if result.get('ids') and len(result.get('ids')) > 0:
                            complete_records = len(result.get('ids'))
                        rec.write({
                            'error_rows': json.dumps([row + index_for_header for row in error_rows]),
                            'complete_records': complete_records,
                            'file_length': file_length
                        })
                    else:
                        rec.write({
                            'error_rows': False,
                            'complete_records': rec.file_length,
                            'file_length': file_length
                        })
                    rec.make_file_log_invalid_records(error_rows=error_rows)
                    rec.make_file_record_done_from_rule(result_ids=result.get('ids'), error_rows=error_rows)
                    base_import_from_batch.sudo().unlink()
            except Exception as e:
                rec.status = 'error'
                rec.log = str(e)

    def test_execute_import(self):
        for rec in self:
            if rec.file:
                base_import_from_batch = self.with_context(clean_context(json.loads(rec.parent_batch_import_id.context))).env['base_import.import'].create({
                    'file': base64.b64decode(rec.file),
                    'file_name': rec.file_name,
                    'file_type': rec.file_type,
                    'res_model': rec.parent_batch_import_id.res_model,
                })
                options = json.loads(rec.parent_batch_import_id.options)
                fields = json.loads(rec.parent_batch_import_id.list_field)
                columns = json.loads(rec.parent_batch_import_id.columns)
                result = base_import_from_batch.execute_import(fields=fields, columns=columns,
                                                               options=options,
                                                               dryrun=True)
                index_for_header = 2 if options.get('has_headers') else 1
                error_rows = []
                if result.get('messages'):
                    for message in result.get('messages'):
                        if message.get('record'):
                            if message.get('record') not in error_rows:
                                error_rows.append(message.get('record'))
                file_length = result.get('file_length') if result.get('file_length') else rec.parent_batch_import_id.limit
                if len(error_rows) > 0:
                    rec.write({
                        'error_rows': json.dumps([row + index_for_header for row in error_rows]),
                        'file_length': file_length,
                        'log': json.dumps(result, ensure_ascii=False)
                    })
                else:
                    rec.write({
                        'error_rows': False,
                        'file_length': file_length,
                        'log': json.dumps(result, ensure_ascii=False)
                    })
                rec.make_file_log_invalid_records(error_rows=error_rows)
                base_import_from_batch.sudo().unlink()

    def set_to_processing(self, delay_time=0):
        index = 1
        for rec in self:
            rec.status = 'processing'
            rec.log = False
            rec.make_queue_job(delay_time=index * delay_time)
            index = index + 1

    def make_file_log_invalid_records(self, error_rows=[]):
        for rec in self:
            mimetype = rec.file_type
            (file_extension, handler, req) = FILE_TYPE_DICT.get(mimetype, (None, None, None))
            try:
                return getattr(rec, 'make_file_log_invalid_records_' + ('csv' if file_extension == 'csv' else 'exel'))(error_rows=error_rows)
            except Exception as e:
                rec.log = str(e)

    def make_file_log_invalid_records_csv(self, error_rows=[]):
        import pandas as pd
        for rec in self:
            if rec.log:
                if len(error_rows) == 0:
                    error_rows = []
                    if json.loads(rec.log).get('messages'):
                        for message in json.loads(rec.log).get('messages'):
                            if message.get('record'):
                                if message.get('record') not in error_rows:
                                    error_rows.append(message.get('record'))
            if len(error_rows) > 0 and rec.file:
                # sort error_rows
                error_rows.sort()
                decoded_data = base64.b64decode(rec.file)
                df = pd.read_csv(StringIO(decoded_data.decode('utf-8')), dtype=str)
                # Lọc các hàng cần giữ lại
                filtered_df = df[df.index.isin(error_rows)]
                # log error messages
                try:
                    error_dict = {}
                    for message in json.loads(rec.log).get('messages'):
                        if message.get('record'):
                            if message.get('record') not in error_dict:
                                error_dict[message.get('record')] = str(message.get('message'))
                            else:
                                error_dict[message.get('record')] = str(error_dict.get(message.get('record'))) + " + " + str(message.get('message'))
                    # sort dict by key (record)
                    myKeys = list(error_dict.keys())
                    myKeys.sort()
                    sorted_dict = {i: error_dict[i] for i in myKeys}
                    # assign to last column in error file
                    error_messages = [value for value in sorted_dict.values()]
                    if len(error_messages) > 0:
                        filtered_df = filtered_df.assign(Error=error_messages)
                except Exception as e:
                    rec.log = e
                    _logger.error("Can not mapping error message to file log error for batch '%s'", self.file_name or '<unknown>')

                output_data = filtered_df.to_csv(index=False)
                encoded_output_data = base64.b64encode(output_data.encode('utf-8')).decode('utf-8')
                rec.write({
                    'file_invalid_records_name': f"{rec.file_name.split('.')[0]}_invalid_records.{rec.file_name.split('.')[-1]}",
                    'file_invalid_records': encoded_output_data
                })

    def make_file_record_done_from_rule(self, result_ids, error_rows):
        import pandas as pd
        error_rows.sort()
        decoded_data = base64.b64decode(self.file)
        sheet_name = json.loads(self.parent_batch_import_id.options).get('sheet_name') if json.loads(self.parent_batch_import_id.options).get('sheet_name') else "Sheet1"
        df = pd.read_excel(BytesIO(decoded_data), dtype=str)
        # Lọc các hàng cần giữ lại
        try:
            filtered_df = df[[True if x not in error_rows else False for x in df.index.tolist()]]
            products_valid = self.env['product.template'].sudo().search([('id','in',result_ids)])
            filtered_df.update({'Mã SKU': [x.sku_code if x.sku_code else '' for x in products_valid], 'Mã barcode': [x.barcode if x.barcode else '' for x in products_valid]})
            output = BytesIO()
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
            filtered_df.to_excel(writer, sheet_name=sheet_name, index=False)
            writer.close()
            output.seek(0)

            chunk_data = output.read()
            chunk_data_base64 = base64.b64encode(chunk_data)
            self.write({
                'file_record_done_from_rule_name': f"{self.file_name.split('.')[0]}_valid_records.{self.file_name.split('.')[-1]}",
                'file_record_done_from_rule': chunk_data_base64
            })
        except Exception as e:
            self.log = e
            _logger.info(e)

    def make_file_log_invalid_records_exel(self, error_rows=[]):
        import pandas as pd
        for rec in self:
            if rec.log:
                if len(error_rows) == 0:
                    # get error_rows by record
                    error_rows = []
                    if json.loads(rec.log).get('messages'):
                        for message in json.loads(rec.log).get('messages'):
                            if message.get('record'):
                                if message.get('record') not in error_rows:
                                    error_rows.append(message.get('record'))
                sheet_name = json.loads(rec.parent_batch_import_id.options).get('sheet_name') if json.loads(rec.parent_batch_import_id.options).get('sheet_name') else "Sheet1"
                if len(error_rows) > 0 and rec.file:
                    # sort error_rows
                    error_rows.sort()
                    decoded_data = base64.b64decode(rec.file)
                    df = pd.read_excel(BytesIO(decoded_data), dtype=str)
                    # Lọc các hàng cần giữ lại
                    filtered_df = df[df.index.isin(error_rows)]
                    # log error messages
                    try:
                        error_dict = {}
                        for message in json.loads(rec.log).get('messages'):
                            if message.get('record'):
                                if message.get('record') not in error_dict:
                                    error_dict[message.get('record')] = str(message.get('message'))
                                else:
                                    error_dict[message.get('record')] = str(error_dict.get(message.get('record'))) + " + " + str(message.get('message'))
                        # sort dict by key (record)
                        myKeys = list(error_dict.keys())
                        myKeys.sort()
                        sorted_dict = {i: error_dict[i] for i in myKeys}
                        # assign to last column in error file
                        error_messages = [value for value in sorted_dict.values()]
                        if len(error_messages) > 0:
                            filtered_df = filtered_df.assign(Error=error_messages)
                    except Exception as e:
                        rec.log = e
                        _logger.error("Can not mapping error message to file log error for batch '%s'", self.file_name or '<unknown>')

                    output = BytesIO()
                    writer = pd.ExcelWriter(output, engine='xlsxwriter')
                    filtered_df.to_excel(writer, sheet_name=sheet_name, index=False)
                    writer.close()
                    output.seek(0)

                    chunk_data = output.read()
                    chunk_data_base64 = base64.b64encode(chunk_data)
                    rec.write({
                        'file_invalid_records_name': f"{rec.file_name.split('.')[0]}_invalid_records.{rec.file_name.split('.')[-1]}",
                        'file_invalid_records': chunk_data_base64
                    })
