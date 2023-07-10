from odoo.exceptions import ValidationError
import logging
import gzip
import base64
import json
import requests
from Crypto.Cipher import AES

_logger = logging.getLogger(__name__)

disable_create_function = False


def connect_bkav(data, configs):
    # Compress the data using gzip
    compressed_data = gzip.compress(str(data).encode("utf-8"))

    # Decode the partner token
    partner_token = configs.get('partner_token')
    encryption_key, iv = partner_token.split(":")
    encryption_key = base64.b64decode(encryption_key)
    iv = base64.b64decode(iv)

    # Create a padding function to ensure data is padded to a 16 byte boundary
    def pad(data):
        pad_length = 16 - (len(data) % 16)
        return data + bytes([pad_length] * pad_length)

    # Pad the compressed data to a 16 byte boundary
    padded_compressed_data = pad(compressed_data)

    # Create an AES cipher object using the encryption key and CBC mode
    cipher = AES.new(encryption_key, AES.MODE_CBC, iv)

    # Encrypt the padded compressed data
    encrypted_data = cipher.encrypt(padded_compressed_data)

    # Base64 encode the encrypted data
    encrypted_data = base64.b64encode(encrypted_data).decode("utf-8")

    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "http://tempuri.org/ExecCommand"
    }

    soap_request = f"""
                <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tem="http://tempuri.org/">
                   <soapenv:Header/>
                   <soapenv:Body>
                      <ExecCommand xmlns="http://tempuri.org/">
                          <partnerGUID>{configs.get('partner_guid')}</partnerGUID>
                          <CommandData>{encrypted_data}</CommandData>
                      </ExecCommand>
                   </soapenv:Body>
                </soapenv:Envelope>
            """

    response = requests.post(configs.get('bkav_url'), headers=headers, data=soap_request, timeout=3.5)

    mes = response.content.decode("utf-8")

    start_index = mes.index("<ExecCommandResult>") + len("<ExecCommandResult>")
    end_index = mes.index("</ExecCommandResult>")
    res = response.content[start_index:end_index]

    decoded_string = base64.b64decode(res)
    cipher2 = AES.new(encryption_key, AES.MODE_CBC, iv)
    plaintext = cipher2.decrypt(decoded_string)
    plaintext = plaintext.rstrip(plaintext[-1:])
    try:
        result_decode = gzip.decompress(plaintext).decode()
    except Exception as ex:
        _logger.info(f'Nhận khách từ lỗi của BKAV {ex}')
        raise ValidationError(f'Nhận khách từ lỗi của BKAV {ex}')
    return json.loads(result_decode)
    #
    # if response_bkav['Status'] == 0:
    #     if type(response_bkav['Object']) == int:
    #         return response_bkav['Object']
    #     elif type(response_bkav['Object']) == str and len(response_bkav['Object']) == 0:
    #         return response_bkav['Object']
    #     else:
    #         status_index = response_bkav['Object'].index('"Status":') + len('"Status":')
    #         mes_index_s = response_bkav['Object'].index('"MessLog":"') + len('"MessLog":"')
    #         mes_index_e = response_bkav['Object'].index('"}]')
    #         response_status = response_bkav['Object'][status_index]
    #         if response_status == '1':
    #             response_mes = response_bkav['Object']
    #             invoice_guid = ''
    #             invoice_no = ''
    #         else:
    #             response_mes = response_bkav['Object'][mes_index_s:mes_index_e]
    #             invoice_guid = (json.loads(response_bkav['Object']))[0]["InvoiceGUID"]
    #             invoice_no = (json.loads(response_bkav['Object']))[0]["InvoiceNo"]
    # else:
    #     response_status = '1'
    #     response_mes = response_bkav['Object']
    #     invoice_guid = ''
    #     invoice_no = ''
    #
    # return {
    #     'status': response_status,
    #     'message': response_mes,
    #     'invoice_guid': invoice_guid,
    #     'invoice_no': invoice_no,
    # }