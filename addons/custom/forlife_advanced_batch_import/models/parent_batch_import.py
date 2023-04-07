from odoo import api, fields, models
import pandas as pd
from io import BytesIO


class ParentBatchImport(models.Model):
    _name = "parent.batch.import"
    _description = "Manage and configure original file import"
    _rec_name = "res_model"

    res_model = fields.Char(string="Model")
    file = fields.Binary('File', help="File to check and/or import, raw binary (not base64)", attachment=False)
    file_name = fields.Char('File Name')
    list_field = fields.Text(string="List Fields")
    columns = fields.Text(string="Columns")
    options = fields.Text(string="Options")
    dryrun = fields.Boolean(string="Dry Run", help="performs all import operations (and validations) but rollbacks writes, allows getting as much errors as possible without the risk of clobbering the database")
    status = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('done', 'Done'), ('cancel', 'Cancel')], string='Status', default='pending')
    number_of_split_file = fields.Integer(string="Number of split file")
    with_delay = fields.Integer(string="Delay execute between every batch", default=10)
    child_batch_import_ids = fields.One2many(string="Children  Batch", comodel_name="child.batch.import", inverse_name='parent_batch_import_id')

    def create_parent_batch_import(self, fields, columns, options, dryrun=False):
        if options.get('base_import_id'):
            base_import = self.env['base_import.import'].sudo().search([('id', '=', options.get('base_import_id'))], limit=1)
            if base_import:
                batch_import = self.env['parent.batch.import'].sudo().create({
                    'res_model': base_import.res_model,
                    'file': base_import.file,
                    'file_name': base_import.file_name,
                    # 'list_field': fields,
                    # 'columns': columns,
                    # 'options': options,
                    'dryrun': dryrun,
                    'status': 'draft',
                    'with_delay': int(options.get('with_delay')),
                    # 'number_of_split_file': options.get('split_file'),
                })
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                dst_url = "%s/web#id=%s&model=parent.batch.import&view_type=form" % (base_url, batch_import.id)
                byte_chunks = self.split_csv_or_excel_file_from_bytes(base_import.file, options.get('limit'))
                index = 1
                for chunk in byte_chunks:
                    # self.env['child.batch.import'].with_delay(priority=index, eta=int(options.get('with_delay'))).sudo().create({
                    self.env['child.batch.import'].sudo().create({
                        'sequence': index,
                        'parent_batch_import_id': batch_import.id,
                        'file': chunk,
                        'file_name': f"{base_import.file_name.split('.')[0]}_{index}.{base_import.file_name.split('.')[-1]}",
                        'status': 'draft',
                        'skip': 0,
                    })
                    index = index + 1

                return dst_url
        return False

    def split_csv_or_excel_file_from_bytes(self,input_bytes, chunk_size):
        """
        Chia dữ liệu dạng byte thành các đoạn dữ liệu byte nhỏ dựa trên số lượng dòng đã cho.

        Tham số đầu vào:
            - input_bytes (bytes): Dữ liệu đầu vào dạng byte.
            - chunk_size (int): Số lượng dòng tối đa trong mỗi đoạn dữ liệu byte đầu ra.

        Đầu ra:
            - List[bytes]: Danh sách các đoạn dữ liệu byte đã chia nhỏ.
        """
        # Chuyển dữ liệu byte thành đối tượng DataFrame của pandas
        df = pd.read_excel(BytesIO(input_bytes))

        # Chia dataframe thành các dataframe con dựa trên số lượng dòng đã cho
        chunk_start = 0
        chunk_end = chunk_size
        byte_chunks = []
        while chunk_start < len(df):
            df_chunk = df.iloc[chunk_start:chunk_end]
            # Kiểm tra xem dataframe con có dữ liệu không
            if not df_chunk.empty:
                # Chuyển DataFrame thành đối tượng BytesIO để ghi dữ liệu Excel vào
                excel_bytes_io = BytesIO()
                with pd.ExcelWriter(excel_bytes_io, engine='openpyxl') as writer:
                    writer.book = writer.book
                    writer.sheets = {ws.title: ws for ws in writer.sheets}
                    df_chunk.to_excel(writer, index=False)
                    writer.save()
                # Lấy dữ liệu byte từ đối tượng BytesIO
                byte_chunks.append(excel_bytes_io.getvalue())
            chunk_start = chunk_end
            chunk_end += chunk_size

        return byte_chunks
