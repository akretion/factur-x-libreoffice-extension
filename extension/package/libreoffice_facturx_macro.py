# -*- coding: utf-8 -*-
# Copyright Alexis de Lattre <alexis.delattre@akretion.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import uno
import unohelper
from com.sun.star.beans import PropertyValue
from tempfile import NamedTemporaryFile
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from stdnum.eu.vat import is_valid
from stdnum.fr.siret import validate, InvalidChecksum, InvalidComponent, InvalidFormat, InvalidLength
from PyPDF4 import PdfFileWriter, PdfFileReader
from PyPDF4.generic import DictionaryObject, DecodedStreamObject,\
    NameObject, createStringObject, ArrayObject, IndirectObject
from PyPDF4.utils import b_
import hashlib


def msg_box(doc, message):
    oSM = uno.getComponentContext().getServiceManager()
    oToolkit = oSM.createInstance("com.sun.star.awt.Toolkit")
    box_type = "errorbox"
    box_title = "Error"
    box_msg = str(message)
    box_button = 1  # OK button
    oParentWin = doc.getCurrentController().getFrame().getContainerWindow()
    oMsgBox = oToolkit.createMessageBox(oParentWin, box_type, box_button, box_title, box_msg)
    oMsgBox.execute()
    return False


def generate_facturx_xml(data):
    ns = {
        'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        'rsm': 'urn:un:unece:uncefact:data:standard:'
               'CrossIndustryInvoice:100',
        'ram': 'urn:un:unece:uncefact:data:standard:'
               'ReusableAggregateBusinessInformationEntity:100',
        'qdt': 'urn:un:unece:uncefact:data:standard:QualifiedDataType:100',
        'udt': 'urn:un:unece:uncefact:data:'
               'standard:UnqualifiedDataType:100',
        }
    ET.register_namespace('xsi', ns['xsi'])
    ET.register_namespace('rsm', ns['rsm'])
    ET.register_namespace('ram', ns['ram'])
    ET.register_namespace('qdt', ns['qdt'])
    ET.register_namespace('udt', ns['udt'])
    root = ET.Element(ET.QName(ns['rsm'], 'CrossIndustryInvoice'))
    doc_ctx = ET.SubElement(
        root, ET.QName(ns['rsm'], 'ExchangedDocumentContext'))
    ctx_param = ET.SubElement(
        doc_ctx, ET.QName(ns['ram'], 'GuidelineSpecifiedDocumentContextParameter'))
    ctx_param_id = ET.SubElement(ctx_param, ET.QName(ns['ram'], 'ID'))
    ctx_param_id.text = 'urn:factur-x.eu:1p0:minimum'
    header_doc = ET.SubElement(
        root, ET.QName(ns['rsm'], 'ExchangedDocument'))
    header_doc_id = ET.SubElement(header_doc, ET.QName(ns['ram'], 'ID'))
    header_doc_id.text = data['invoice_number']
    header_doc_typecode = ET.SubElement(
        header_doc, ET.QName(ns['ram'], 'TypeCode'))
    if data['invoice_or_refund'] == 'refund':
        header_doc_typecode.text = '381'
    else:
        header_doc_typecode.text = '380'
    date_node = ET.SubElement(header_doc, ET.QName(ns['ram'], 'IssueDateTime'))
    date_node_str = ET.SubElement(
        date_node, ET.QName(ns['udt'], 'DateTimeString'), format='102')
    # 102 = format YYYYMMDD
    date_node_str.text = data['invoice_date'].strftime('%Y%m%d')
    trade_transaction = ET.SubElement(
        root, ET.QName(ns['rsm'], 'SupplyChainTradeTransaction'))
    trade_agreement = ET.SubElement(
        trade_transaction,
        ET.QName(ns['ram'], 'ApplicableHeaderTradeAgreement'))
    if data.get('customer_chorus_service_code'):
        buyer_reference = ET.SubElement(
            trade_agreement, ET.QName(ns['ram'], 'BuyerReference'))
        buyer_reference.text = data['customer_chorus_service_code']
    seller = ET.SubElement(trade_agreement, ET.QName(ns['ram'], 'SellerTradeParty'))
    seller_name = ET.SubElement(seller, ET.QName(ns['ram'], 'Name'))
    seller_name.text = data['issuer_name']
    seller_legal_org = ET.SubElement(
        seller, ET.QName(ns['ram'], 'SpecifiedLegalOrganization'))
    seller_legal_org_id = ET.SubElement(
        seller_legal_org, ET.QName(ns['ram'], 'ID'), schemeID='0002')
    seller_legal_org_id.text = data['issuer_siret']
    seller_country = ET.SubElement(
        seller, ET.QName(ns['ram'], 'PostalTradeAddress'))
    seller_country_code = ET.SubElement(
        seller_country, ET.QName(ns['ram'], 'CountryID'))
    seller_country_code.text = data['issuer_country_code']
    seller_tax_reg = ET.SubElement(
        seller, ET.QName(ns['ram'], 'SpecifiedTaxRegistration'))
    seller_tax_reg_id = ET.SubElement(
        seller_tax_reg, ET.QName(ns['ram'], 'ID'), schemeID='VA')
    seller_tax_reg_id.text = data['issuer_vat_number']
    buyer = ET.SubElement(trade_agreement, ET.QName(ns['ram'], 'BuyerTradeParty'))
    buyer_name = ET.SubElement(buyer, ET.QName(ns['ram'], 'Name'))
    buyer_name.text = data['customer_name']
    if data.get('customer_siret'):
        buyer_legal_org = ET.SubElement(
            buyer, ET.QName(ns['ram'], 'SpecifiedLegalOrganization'))
        buyer_legal_org_id = ET.SubElement(
            buyer_legal_org, ET.QName(ns['ram'], 'ID'), schemeID='0002')
        buyer_legal_org_id.text = data['customer_siret']
    buyer_country = ET.SubElement(
        buyer, ET.QName(ns['ram'], 'PostalTradeAddress'))
    buyer_country_code = ET.SubElement(
        buyer_country, ET.QName(ns['ram'], 'CountryID'))
    buyer_country_code.text = data['customer_country_code']
    if data.get('customer_vat_number'):
        buyer_tax_reg = ET.SubElement(
            buyer, ET.QName(ns['ram'], 'SpecifiedTaxRegistration'))
        buyer_tax_reg_id = ET.SubElement(
            buyer_tax_reg, ET.QName(ns['ram'], 'ID'), schemeID='VA')
        buyer_tax_reg_id.text = data['customer_vat_number']
    if data.get('customer_order_ref'):
        buyer_order_ref = ET.SubElement(
            trade_agreement, ET.QName(ns['ram'], 'BuyerOrderReferencedDocument'))
        buyer_order_id = ET.SubElement(
            buyer_order_ref, ET.QName(ns['ram'], 'IssuerAssignedID'))
        buyer_order_id.text = data['customer_order_ref']
    ET.SubElement(
        trade_transaction, ET.QName(ns['ram'], 'ApplicableHeaderTradeDelivery'))
    trade_settlement = ET.SubElement(
        trade_transaction, ET.QName(ns['ram'], 'ApplicableHeaderTradeSettlement'))
    invoice_currency = ET.SubElement(
        trade_settlement, ET.QName(ns['ram'], 'InvoiceCurrencyCode'))
    invoice_currency.text = data['invoice_currency']
    sums = ET.SubElement(
        trade_settlement,
        ET.QName(ns['ram'], 'SpecifiedTradeSettlementHeaderMonetarySummation'))
    tax_basis_total_amt = ET.SubElement(
        sums, ET.QName(ns['ram'], 'TaxBasisTotalAmount'))
    tax_basis_total_amt.text = '%.2f' % data['total_without_tax']
    tax_total = ET.SubElement(
        sums, ET.QName(ns['ram'], 'TaxTotalAmount'), currencyID=data['invoice_currency'])
    tax_total.text = '%.2f' % data['total_tax']
    total = ET.SubElement(sums, ET.QName(ns['ram'], 'GrandTotalAmount'))
    total.text = '%.2f' % data['total_with_tax']
    residual = ET.SubElement(sums, ET.QName(ns['ram'], 'DuePayableAmount'))
    residual.text = '%.2f' % data['total_due']
    xml_byte = ET.tostring(root)
    return xml_byte


def open_filepicker(path=None, mode=10):
    """
    Possible modes: http://api.libreoffice.org/docs/idl/ref/namespacecom_1_1sun_1_1star_1_1ui_1_1dialogs_1_1TemplateDescription.html
    mode 10 : with option "automatic file name extension"
    """
    oCtx = uno.getComponentContext()
    oServiceManager = oCtx.getServiceManager()

    filepicker = oServiceManager.createInstanceWithArgumentsAndContext(
        "com.sun.star.ui.dialogs.OfficeFilePicker", (mode,), oCtx)
    if path:
        filepicker.setDisplayDirectory(path)
    filepicker.appendFilter("PDF Files (.pdf)", "*.pdf")
    filepicker.Title = 'Save Factur-X PDF As'
    if filepicker.execute():
        return filepicker.getFiles()[0]


def check_data(doc, data):
    fields = {
        'issuer_name': {
            'type': 'char',
            'required': True,
            },
        'issuer_vat_number': {
            'type': 'char',
            'required': False,
            },
        'issuer_siret': {
            'type': 'char',
            'required': False,
            },
        'issuer_country_code': {
            'type': 'char',
            'required': True,
            },
        'customer_name': {
            'type': 'char',
            'required': True,
            },
        'customer_vat_number': {
            'type': 'char',
            'required': False,
            },
        'customer_siret': {
            'type': 'char',
            'required': False,
            },
        'customer_country_code': {
            'type': 'char',
            'required': True,
            },
        'customer_chorus_service_code': {
            'type': 'char',
            'required': True,
            },
        'customer_order_ref': {
            'type': 'char',
            'required': False,
            },
        'invoice_or_refund': {
            'type': 'char',
            'required': False,
            },
        'invoice_number': {
            'type': 'char',
            'required': True,
            },
        'invoice_date': {
            'type': 'date',
            'required': True,
            },
        'invoice_currency': {
            'type': 'char',
            'required': True,
            },
        'total_without_tax': {
            'type': 'float',
            'required': True,
            },
        'total_tax': {
            'type': 'float',
            'required': True,
            },
        'total_with_tax': {
            'type': 'float',
            'required': True,
            },
        'total_due': {
            'type': 'float',
            'required': True,
            },
        }
    for field, fdict in fields.items():
        # check required fields are set
        if fdict['required']:
            if field not in data:
                return msg_box(doc, "Missing field %s in the 'Data' tab." % field)
        if field in data:
            msg_start = "Field '%s' has value '%s'; "
            msg_vals = (field, data[field])
            # check type
            if fdict['type'] == 'float':
                if not isinstance(data[field], float):
                    return msg_box(doc, (msg_start + "it should be a float.") % msg_vals)
                if data[field] < 0:
                    return msg_box(doc, (msg_start + "it should be positive.") % msg_vals)
            elif fdict['type'] == 'date':
                if not isinstance(data[field], datetime):
                    return msg_box(doc, (msg_start + "it should be a date.") % msg_vals)
            elif fdict['type'] == 'char':
                if not isinstance(data[field], str):
                    return msg_box(doc, (msg_start + "it should be a string.") % msg_vals)
                data[field] = data[field].strip()
            # check specific fields
            if field.endswith('country_code'):  # required field
                if len(data[field]) != 2 or not data[field].isalpha():
                    return msg_box(doc, (msg_start + "country codes must have 2 letters.") % msg_vals)
                data[field] = data[field].upper()
            if field.endswith('_siret') and data[field]:
                data[field] = data[field].replace(' ', '')
                try:
                    validate(data[field])
                except (InvalidChecksum, InvalidComponent, InvalidFormat, InvalidLength) as e:
                    return msg_box(doc, (msg_start + str(e)) % msg_vals)
            if field.endswith('_vat_number'):
                data[field] = data[field].replace(' ', '').upper()
                if not is_valid(data[field]):
                    return msg_box(doc, (msg_start + "the VAT number is invalid.") % msg_vals)
            if field == 'invoice_currency':  # required field
                if len(data[field]) != 3 or not data[field].isalpha():
                    return msg_box(doc, (msg_start + "it should have 3 letters.") % msg_vals)
                data[field] = data[field].upper()
            elif field == 'invoice_date':
                near_future = datetime.today() + timedelta(days=3)
                distant_past = datetime.today() - timedelta(days=5*365)
                if data['invoice_date'] > near_future or data['invoice_date'] < distant_past:
                    return msg_box(doc, (msg_start + "it must be in the not-so-distant past, in the present or in the very near future.") % (field, data[field].strftime('%Y-%m-%d')))

    # Global checks
    if data['issuer_country_code'] == 'FR' and not data['issuer_siret']:
        return msg_box(doc, "Field '%s' must have a value because the issuer's country is France.")
    diff = data['total_with_tax'] - data['total_without_tax'] - data['total_tax']
    if abs(diff) > 0.00001:
        return msg_box(doc, "Field 'total_with_tax' (%s) must be equal to 'total_without_tax' (%s) plus 'total_tax' (%s)." % (data['total_with_tax'], data['total_without_tax'], data['total_tax']))
    if data['total_due'] - 0.00001 > data['total_with_tax']:
        return msg_box(doc, "Field 'total_due' (%s) cannot be superior to 'total_with_tax' (%s)." % (data['total_due'], data['total_with_tax']))
    if not data.get('invoice_or_refund'):
        data['invoice_or_refund'] = 'invoice'  # default value
    if data['invoice_or_refund'].lower() not in ('invoice', 'refund'):
        return msg_box(doc, "Field 'invoice_or_refund' has value '%s'; it should be either 'invoice' or 'refund'." % data['invoice_or_refund'])
    return True


def generate_facturx_invoice_v1(button_arg=None):
    doc = XSCRIPTCONTEXT.getDocument()
    data_sheet = doc.Sheets.getByName('Data')
    if not data_sheet:
        return msg_box(doc, "Missing 'Data' tab in the spreadsheet.")
    inv_sheet = doc.Sheets.getByName('Invoice')
    if not inv_sheet:
        return msg_box(doc, "Missing 'Invoice' tab in the spreadsheet.")
    data = {}
    for i in range(50):
        keycell = data_sheet.getCellByPosition(0, i)
        key = keycell.String
        valuecell = data_sheet.getCellByPosition(1, i)
        if key.startswith('total_'):
            value = valuecell.Value
        elif key.endswith('_date'):
            # when the cell is not recognised as a date, valuecell.Value = 0.0
            if valuecell.Value < 2:
                return msg_box(doc, "Field '%s' doesn't seem to be a date field. Check the type of the cell has a date format. For that, right clic on the cell and select 'Format Cells': in the first tab, select 'Date' as 'Category' and check that the selected 'Format' matches the way you entered the date in the cell." % key)
            date_as_int = int(valuecell.Value)
            value = datetime.fromordinal(datetime(1900, 1, 1).toordinal() + date_as_int - 2)
        else:
            value = valuecell.String
        if key and value:
            data[key] = value

    # filter data
    res_check = check_data(doc, data)
    if not res_check:
        return

    # prepare LO PDF export
    pdf_option1 = PropertyValue()
    pdf_option1.Name = "SelectPdfVersion"  # PDF/A
    pdf_option1.Value = 1
    pdf_option2 = PropertyValue()
    pdf_option2.Name = "Selection"  # Export 'Invoice' tab
    pdf_option2.Value = inv_sheet
    pdf_options = (pdf_option1, pdf_option2)

    pdf_export_arg1 = PropertyValue()
    pdf_export_arg1.Name = "FilterName"
    pdf_export_arg1.Value = "calc_pdf_Export"
    pdf_export_arg2 = PropertyValue()
    pdf_export_arg2.Name = "FilterData"
    pdf_export_arg2.Value = uno.Any("[]com.sun.star.beans.PropertyValue", pdf_options)
    pdf_export_args = (pdf_export_arg1, pdf_export_arg2)

    pdf_tmp_file = NamedTemporaryFile('w', prefix='libo-fx-', suffix='.pdf')
    pdf_tmp_file_url = uno.systemPathToFileUrl(pdf_tmp_file.name)
    doc.storeToURL(pdf_tmp_file_url, pdf_export_args)

    # generate XML
    xml_byte = generate_facturx_xml(data)
    if not xml_byte:
        return

    # open "save-as" dialog box
    fx_pdf_filename_url = open_filepicker()
    if not fx_pdf_filename_url:  # when the user click on cancel in the dialog box
        return
    fx_pdf_filename = uno.fileUrlToSystemPath(fx_pdf_filename_url)

    pdf_metadata = {
        'author': data['issuer_name'],
        'keywords': 'Factur-X, Invoice',
        'title': '%s: Invoice %s' % (
            data['issuer_name'], data['invoice_number']),
        'subject': 'Factur-X invoice %s issued by %s' % (
            data['invoice_number'], data['issuer_name']),
        }

    generate_facturx_from_file(
        pdf_tmp_file.name, xml_byte, facturx_level='minimum',
        check_xsd=False, pdf_metadata=pdf_metadata,
        output_pdf_file=fx_pdf_filename)
    pdf_tmp_file.close()
    return

##################################################
# Include parts of my factur-x python lib here
# Why include the factur-x lib here instead of providing
# it under package/pythonpath as the PyPDF4 and stdnum libs ?
# Because the factur-x lib depends on lxml,
# and lxml is a Python binding on a C lib,
# which causes portability issues.
# So I decided to extract the parts of the factur-x lib that
# we need for this macro in this file (these parts don't depend
# on the lxml lib any more).


__version__ = '1.5libmacro'

FACTURX_FILENAME = 'factur-x.xml'
FACTURX_LEVEL2xmp = {
    'minimum': 'MINIMUM',
    'basicwl': 'BASIC WL',
    'basic': 'BASIC',
    'en16931': 'EN 16931',
    'extended': 'EXTENDED',
    }


def _get_dict_entry(node, entry):
    if not isinstance(node, dict):
        raise ValueError('The node must be a dict')
    dict_entry = node.get(entry)
    if isinstance(dict_entry, dict):
        return dict_entry
    elif isinstance(dict_entry, IndirectObject):
        res_dict_entry = dict_entry.getObject()
        if isinstance(res_dict_entry, dict):
            return res_dict_entry
        else:
            return False
    else:
        return False


def _get_pdf_timestamp(date=None):
    if date is None:
        date = datetime.now()
    # example date format: "D:20141006161354+02'00'"
    pdf_date = date.strftime("D:%Y%m%d%H%M%S+00'00'")
    return pdf_date


def _get_metadata_timestamp():
    now_dt = datetime.now()
    # example format : 2014-07-25T14:01:22+02:00
    meta_date = now_dt.strftime('%Y-%m-%dT%H:%M:%S+00:00')
    return meta_date


def _prepare_pdf_metadata_txt(pdf_metadata):
    pdf_date = _get_pdf_timestamp()
    info_dict = {
        '/Author': pdf_metadata.get('author', ''),
        '/CreationDate': pdf_date,
        '/Creator':
        'factur-x Python lib v%s by Alexis de Lattre' % __version__,
        '/Keywords': pdf_metadata.get('keywords', ''),
        '/ModDate': pdf_date,
        '/Subject': pdf_metadata.get('subject', ''),
        '/Title': pdf_metadata.get('title', ''),
        }
    return info_dict


def _prepare_pdf_metadata_xml(facturx_level, pdf_metadata):
    xml_str = """
<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/" rdf:about="">
      <pdfaid:part>3</pdfaid:part>
      <pdfaid:conformance>B</pdfaid:conformance>
    </rdf:Description>
    <rdf:Description xmlns:dc="http://purl.org/dc/elements/1.1/" rdf:about="">
      <dc:title>
        <rdf:Alt>
          <rdf:li xml:lang="x-default">${title}</rdf:li>
        </rdf:Alt>
      </dc:title>
      <dc:creator>
        <rdf:Seq>
          <rdf:li>${author}</rdf:li>
        </rdf:Seq>
      </dc:creator>
      <dc:description>
        <rdf:Alt>
          <rdf:li xml:lang="x-default">${subject}</rdf:li>
        </rdf:Alt>
      </dc:description>
    </rdf:Description>
    <rdf:Description xmlns:pdf="http://ns.adobe.com/pdf/1.3/" rdf:about="">
      <pdf:Producer>${producer}</pdf:Producer>
    </rdf:Description>
    <rdf:Description xmlns:xmp="http://ns.adobe.com/xap/1.0/" rdf:about="">
      <xmp:CreatorTool>${creator_tool}</xmp:CreatorTool>
      <xmp:CreateDate>${timestamp}</xmp:CreateDate>
      <xmp:ModifyDate>${timestamp}</xmp:ModifyDate>
    </rdf:Description>
    <rdf:Description xmlns:pdfaExtension="http://www.aiim.org/pdfa/ns/extension/" xmlns:pdfaSchema="http://www.aiim.org/pdfa/ns/schema#" xmlns:pdfaProperty="http://www.aiim.org/pdfa/ns/property#" rdf:about="">
      <pdfaExtension:schemas>
        <rdf:Bag>
          <rdf:li rdf:parseType="Resource">
            <pdfaSchema:schema>Factur-X PDFA Extension Schema</pdfaSchema:schema>
            <pdfaSchema:namespaceURI>urn:factur-x:pdfa:CrossIndustryDocument:invoice:1p0#</pdfaSchema:namespaceURI>
            <pdfaSchema:prefix>fx</pdfaSchema:prefix>
            <pdfaSchema:property>
              <rdf:Seq>
                <rdf:li rdf:parseType="Resource">
                  <pdfaProperty:name>DocumentFileName</pdfaProperty:name>
                  <pdfaProperty:valueType>Text</pdfaProperty:valueType>
                  <pdfaProperty:category>external</pdfaProperty:category>
                  <pdfaProperty:description>name of the embedded XML invoice file</pdfaProperty:description>
                </rdf:li>
                <rdf:li rdf:parseType="Resource">
                  <pdfaProperty:name>DocumentType</pdfaProperty:name>
                  <pdfaProperty:valueType>Text</pdfaProperty:valueType>
                  <pdfaProperty:category>external</pdfaProperty:category>
                  <pdfaProperty:description>INVOICE</pdfaProperty:description>
                </rdf:li>
                <rdf:li rdf:parseType="Resource">
                  <pdfaProperty:name>Version</pdfaProperty:name>
                  <pdfaProperty:valueType>Text</pdfaProperty:valueType>
                  <pdfaProperty:category>external</pdfaProperty:category>
                  <pdfaProperty:description>The actual version of the Factur-X XML schema</pdfaProperty:description>
                </rdf:li>
                <rdf:li rdf:parseType="Resource">
                  <pdfaProperty:name>ConformanceLevel</pdfaProperty:name>
                  <pdfaProperty:valueType>Text</pdfaProperty:valueType>
                  <pdfaProperty:category>external</pdfaProperty:category>
                  <pdfaProperty:description>The conformance level of the embedded Factur-X data</pdfaProperty:description>
                </rdf:li>
              </rdf:Seq>
            </pdfaSchema:property>
          </rdf:li>
        </rdf:Bag>
      </pdfaExtension:schemas>
    </rdf:Description>
    <rdf:Description xmlns:fx="urn:factur-x:pdfa:CrossIndustryDocument:invoice:1p0#" rdf:about="">
      <fx:DocumentType>${facturx_documenttype}</fx:DocumentType>
      <fx:DocumentFileName>${facturx_filename}</fx:DocumentFileName>
      <fx:Version>${facturx_version}</fx:Version>
      <fx:ConformanceLevel>${facturx_level}</fx:ConformanceLevel>
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>
"""
    replace_dict = {
        'title': pdf_metadata.get('title', ''),
        'author': pdf_metadata.get('author', ''),
        'subject': pdf_metadata.get('subject', ''),
        'producer': 'PyPDF4',
        'creator_tool': 'factur-x python lib v%s by Alexis de Lattre' % __version__,
        'timestamp': _get_metadata_timestamp(),
        'facturx_documenttype': 'INVOICE',
        'facturx_filename': FACTURX_FILENAME,
        'facturx_version': '1.0',
        'facturx_level': FACTURX_LEVEL2xmp[facturx_level],
        }
    for replace_key, replace_value in replace_dict.items():
        xml_str = xml_str.replace('${%s}' % replace_key, replace_value)
    xml_byte = xml_str.encode('utf-8')
    return xml_byte


def _facturx_update_metadata_add_attachment(
        pdf_filestream, facturx_xml_str, pdf_metadata, facturx_level,
        output_intents=[], additional_attachments={}):
    '''This method is inspired from the code of the addAttachment()
    method of the PyPDF2 lib'''
    # The entry for the file
    # facturx_xml_str = facturx_xml_str.encode('utf-8')
    md5sum = hashlib.md5(facturx_xml_str).hexdigest()
    md5sum_obj = createStringObject(md5sum)
    params_dict = DictionaryObject({
        NameObject('/CheckSum'): md5sum_obj,
        NameObject('/ModDate'): createStringObject(_get_pdf_timestamp()),
        NameObject('/Size'): NameObject(str(len(facturx_xml_str))),
        })
    file_entry = DecodedStreamObject()
    file_entry.setData(facturx_xml_str)  # here we integrate the file itself
    file_entry.update({
        NameObject("/Type"): NameObject("/EmbeddedFile"),
        NameObject("/Params"): params_dict,
        # 2F is '/' in hexadecimal
        NameObject("/Subtype"): NameObject("/text#2Fxml"),
        })
    file_entry_obj = pdf_filestream._addObject(file_entry)
    # The Filespec entry
    ef_dict = DictionaryObject({
        NameObject("/F"): file_entry_obj,
        NameObject('/UF'): file_entry_obj,
        })

    fname_obj = createStringObject(FACTURX_FILENAME)
    filespec_dict = DictionaryObject({
        NameObject("/AFRelationship"): NameObject("/Data"),
        NameObject("/Desc"): createStringObject("Factur-X Invoice"),
        NameObject("/Type"): NameObject("/Filespec"),
        NameObject("/F"): fname_obj,
        NameObject("/EF"): ef_dict,
        NameObject("/UF"): fname_obj,
        })
    filespec_obj = pdf_filestream._addObject(filespec_dict)
    name_arrayobj_cdict = {fname_obj: filespec_obj}
    name_arrayobj_content_sort = list(
        sorted(name_arrayobj_cdict.items(), key=lambda x: x[0]))
    name_arrayobj_content_final = []
    af_list = []
    for (fname_obj, filespec_obj) in name_arrayobj_content_sort:
        name_arrayobj_content_final += [fname_obj, filespec_obj]
        af_list.append(filespec_obj)
    embedded_files_names_dict = DictionaryObject({
        NameObject("/Names"): ArrayObject(name_arrayobj_content_final),
        })
    # Then create the entry for the root, as it needs a
    # reference to the Filespec
    embedded_files_dict = DictionaryObject({
        NameObject("/EmbeddedFiles"): embedded_files_names_dict,
        })
    res_output_intents = []
    for output_intent_dict, dest_output_profile_dict in output_intents:
        dest_output_profile_obj = pdf_filestream._addObject(
            dest_output_profile_dict)
        # TODO detect if there are no other objects in output_intent_dest_obj
        # than /DestOutputProfile
        output_intent_dict.update({
            NameObject("/DestOutputProfile"): dest_output_profile_obj,
            })
        output_intent_obj = pdf_filestream._addObject(output_intent_dict)
        res_output_intents.append(output_intent_obj)
    # Update the root
    metadata_xml_str = _prepare_pdf_metadata_xml(facturx_level, pdf_metadata)
    metadata_file_entry = DecodedStreamObject()
    metadata_file_entry.setData(metadata_xml_str)
    metadata_file_entry.update({
        NameObject('/Subtype'): NameObject('/XML'),
        NameObject('/Type'): NameObject('/Metadata'),
        })
    metadata_obj = pdf_filestream._addObject(metadata_file_entry)
    af_value_obj = pdf_filestream._addObject(ArrayObject(af_list))
    pdf_filestream._root_object.update({
        NameObject("/AF"): af_value_obj,
        NameObject("/Metadata"): metadata_obj,
        NameObject("/Names"): embedded_files_dict,
        # show attachments when opening PDF
        NameObject("/PageMode"): NameObject("/UseAttachments"),
        })
    if res_output_intents:
        pdf_filestream._root_object.update({
            NameObject("/OutputIntents"): ArrayObject(res_output_intents),
        })
    metadata_txt_dict = _prepare_pdf_metadata_txt(pdf_metadata)
    pdf_filestream.addMetadata(metadata_txt_dict)


def _get_original_output_intents(original_pdf):
    output_intents = []
    try:
        pdf_root = original_pdf.trailer['/Root']
        ori_output_intents = pdf_root['/OutputIntents']
        for ori_output_intent in ori_output_intents:
            ori_output_intent_dict = ori_output_intent.getObject()
            dest_output_profile_dict =\
                ori_output_intent_dict['/DestOutputProfile'].getObject()
            output_intents.append(
                (ori_output_intent_dict, dest_output_profile_dict))
    except Exception:
        pass
    return output_intents


def generate_facturx_from_file(
        pdf_invoice, facturx_xml, facturx_level='autodetect',
        check_xsd=True, pdf_metadata=None, output_pdf_file=None,
        additional_attachments=None):
    """
    Generate a Factur-X invoice from a regular PDF invoice and a factur-X XML
    file. The method uses a file as input (regular PDF invoice) and re-writes
    the file (Factur-X PDF invoice).
    :param pdf_invoice: the regular PDF invoice as file path
    (type string) or as file object
    :type pdf_invoice: string or file
    :param facturx_xml: the Factur-X XML
    :type facturx_xml: bytes, string, file or etree object
    :param facturx_level: the level of the Factur-X XML file. Default value
    is 'autodetect'. The only advantage to specifiy a particular value instead
    of using the autodetection is for a very very small perf improvement.
    Possible values: minimum, basicwl, basic, en16931.
    :type facturx_level: string
    :param check_xsd: if enable, checks the Factur-X XML file against the XSD
    (XML Schema Definition). If this step has already been performed
    beforehand, you should disable this feature to avoid a double check
    and get a small performance improvement.
    :type check_xsd: boolean
    :param pdf_metadata: Specify the metadata of the generated Factur-X PDF.
    If pdf_metadata is None (default value), this lib will generate some
    metadata in English by extracting relevant info from the Factur-X XML.
    Here is an example for the pdf_metadata argument:
    pdf_metadata = {
        'author': 'Akretion',
        'keywords': 'Factur-X, Invoice',
        'title': 'Akretion: Invoice I1242',
        'subject':
          'Factur-X invoice I1242 dated 2017-08-17 issued by Akretion',
        }
    If you pass the pdf_metadata argument, you will not use the automatic
    generation based on the extraction of the Factur-X XML file, which will
    bring a very small perf improvement.
    :type pdf_metadata: dict
    :param output_pdf_file: File Path to the output Factur-X PDF file
    :type output_pdf_file: string or unicode
    :param additional_attachments: Specify the other files that you want to
    embed in the PDF file. It is a dict where keys are filepath and value
    is the description of the file (as unicode or string).
    :type additional_attachments: dict
    :return: Returns True. This method re-writes the input PDF invoice file,
    unless if the output_pdf_file is provided.
    :rtype: bool
    """
    assert isinstance(facturx_xml, bytes)
    xml_string = facturx_xml
    facturx_level = facturx_level.lower()
    original_pdf = PdfFileReader(pdf_invoice)
    # Extract /OutputIntents obj from original invoice
    output_intents = _get_original_output_intents(original_pdf)
    new_pdf_filestream = PdfFileWriter()
    new_pdf_filestream._header = b_("%PDF-1.6")
    new_pdf_filestream.appendPagesFromReader(original_pdf)

    original_pdf_id = original_pdf.trailer.get('/ID')
    if original_pdf_id:
        new_pdf_filestream._ID = original_pdf_id
        # else : generate some ?
    _facturx_update_metadata_add_attachment(
        new_pdf_filestream, xml_string, pdf_metadata, facturx_level,
        output_intents=output_intents)
    if output_pdf_file:
        with open(output_pdf_file, 'wb') as output_f:
            new_pdf_filestream.write(output_f)
            output_f.close()
    else:
        with open(pdf_invoice, 'wb') as f:
            new_pdf_filestream.write(f)
            f.close()
    return True


# Only show the main method to the users
g_exportedScripts = generate_facturx_invoice_v1,

# Declare this Python file as a Macro in libreoffice
g_ImplementationHelper = unohelper.ImplementationHelper()

g_ImplementationHelper.addImplementation(
    None,
    "org.openoffice.script.DummyImplementationForPythonScripts",
    ("org.openoffice.script.DummyServiceForPythonScripts",),)
