.. image:: https://img.shields.io/badge/license-GPL--3-blue.png
   :target: https://www.gnu.org/licenses/gpl
   :alt: License: GPL-3

==============================
LibreOffice Factur-X Extension
==============================

This project provides a `LibreOffice <https://www.libreoffice.org/>`_ Extension to generate `Factur-X <http://fnfe-mpe.org/factur-x/>`_ invoices from a spreadsheet. This extension provides a Python macro that can generate a PDF Factur-X invoice or refund at the Minimum profile. These invoices are compatible with `Chorus Pro <https://chorus-pro.gouv.fr/>`_, the e-invoicing plateform of the French administration.

The aim of this project is to allow small companies that don't have an ERP or invoicing software to generate state-of-the-art electronic invoices. With this LibreOffice extension, we can now say that the generation of Factur-X invoices is not limited to companies with a modern ERP: even a tiny company without any IT skills can generate a Factur-X invoice with a simple spreadsheet. And they can do it at no cost using free software only!

The key targets of this project are:

- easy installation: no IT skills needed,
- multi-platform: Windows, Mac OS, Linux,
- work offline: no Internet connexion needed to generate a Factur-X invoice,
- simplicity and usability for daily invoice generation,
- multi-language: available in French and English (translation to other languages welcomed).

This extension has been initially developped by Alexis de Lattre from `Akretion France <https://akretion.com/>`_. It is published under the `GPL licence <https://www.gnu.org/licenses/gpl-3.0.html>`_.

===============
Video tutorials
===============

A video tutorial that shows how to install and use this LibreOffice extension is available:

* in English: `Youtube link <https://www.youtube.com/watch?v=ldD-1W8yIv0>`_
* in French: `Youtube link <https://www.youtube.com/watch?v=VDm8qUgtkfM>`_

=============
Release notes
=============

* Version 0.16 dated December 31st 2019:

  * FIX: field *Customer Service Code for Chorus Pro* not declared as required field any more
  * FIX: avoid crash when fields *Issuer SIRET* or *Issuer VAT Number* were empty

* Version 0.15 dated Christmas 2019: first public release.

====================
Roadmap - Known bugs
====================

* Translate to German and other languages
* Add installation instructions for Linux distros other than Debian/Ubuntu
* Lobby to have native support for attachments in LibreOffice PDF export, which would simplify a lot this extension!

Contributions and pull requests are welcomed.

============
Installation
============

Pre-requisite for Windows and Mac OS
------------------------------------

It is recommended to have LibreOffice 6.2.0 or higher. If your version is older, download a newer version from the `LibreOffice website <https://www.libreoffice.org/download/download/>`_.

Pre-requisite for Linux Debian/Ubuntu
-------------------------------------

Add the support for Python macros for LibreOffice:

.. code::

  sudo apt install libreoffice-script-provider-python

Pre-requisite for Fedora and Mageia Linux
-----------------------------------------

No need to install any additional package to support Python macros in LibreOffice.

Installation steps
------------------

1. Download the LibreOffice extension **factur-x_macro.oxt**.
#. Open this file with LibreOffice; it will automatically open the LibreOffice extension manager and propose you to install or upgrade the extension. At the end of the installation, a message will inform you that you need to restart LibreOffice.

If you have LibreOffice older than 6.2.0, you will have a message during installation saying that you need a Java Development Kit (JDK) from Oracle. Please ignore the message, **Java is NOT required** to use this extension. This message is a `bug <https://bugs.documentfoundation.org/show_bug.cgi?id=120363>`_ which was fixed in LibreOffice 6.2.0.

=====
Usage
=====

How it works
------------

Get the sample invoice for your language:

* in English: **factur-X_english_invoice_sample.ods**
* In French: **factur-X_modele_facture_francais.ods**

You should cutomize this invoice sample for your company (replace the company name, address, logo, VAT number, etc).

The macro to generate Factur-X invoices will work if the spreadsheet complies with the following rules:

1. The speadsheet must have at least 2 tabs.
#. The 1st tab must contain the invoice. It is that tab which is exported to PDF.
#. The 2nd tab must contain the data used to generate the XML file that will be embedded in the PDF. The values are located in the second column of that tab. The macro will read each information in a specific cell. Therefore, you mustn't change the location of each information in that tab.
#. In the 2nd tab, some information are required for Factur-X. Among the optional information of the Factur-X standard, some information are required for Chorus Pro. Moreover, if the invoice is for Chorus Pro, be aware that some public entities require the use of a *service code* and/or an *engagement number* (equivalent of a purchase order number in the private sector), so these information cannot be left empty if the invoice is for such public entities. The background color of each cell will tell you which are the required information for Factur-X and Chorus Pro (refer to the legend at the bottom of the second tab).
#. In the 2nd tab, the third column will tell you the type of each cell (char, date, float) and its constraints.

In the sample invoice, you will see that the values of the 2nd tab are automatically taken from the data of the 1st tab (via a simple **=** or a formula) except for the currency code (EUR by default). This avoids to copy the information from the 1st tab to the 2nd tab. But it is still recommended to have a fast check of the values of the 2nd tab before generating the Factur-X invoice.

Make it work
------------

To run the macro that will generate the Factur-X PDF invoice, click on the button *Generate Factur-X PDF invoice* at the bottom of the 2nd tab and follow the instructions.

If the button doesn't work, go to the menu *Tools > Macros > Run Macro*. Then open *My Macros > factur-x_macro.oxt > libreoffice_facturx_macro*; in the right column, select the macro *generate_facturx_invoice_v1* and click on the button *Run*; then follow the instructions.

If you want to check the result...
----------------------------------

The XML file embedded in the Factur-X PDF file is named **factur-x.xml**. To view and/or save it, open the PDF file in a modern PDF reader that is able to read attachments in PDF:

* `Acrobat Reader <https://get.adobe.com/reader/>`_: click on the paper clip icon on the left side bar to view the attachments.
* `Firefox <https://www.mozilla.org/firefox/>`_ (recent versions only): click on the paper clip icon at the top left.
* `SumatraPDF <https://www.sumatrapdfreader.org/>`_ (Windows): attachments automatically appear on the left side.
* `Evince <https://wiki.gnome.org/Apps/Evince>`_ (Linux/Gnome): in the drop-down list at the top left, select *Attachments*.
* `Okular <https://okular.kde.org/>`_ (Linux/KDE): a blue banner automatically appears at the top when the PDF file has attachments.

==============
About Factur-X
==============

Factur-X is a franco-german e-invoicing standard that is based on a simple concept: a PDF invoice that embeds an XML file in CrossIndustryInvoice (CII) format. The specifications of the Factur-X standard are available in French and English on the website of the `FNFE-MPE <http://fnfe-mpe.org/factur-x/>`_. The Factur-X standard has 5 profiles that correspond to 5 levels of details in the information provided in the XML file: Minimum, Basic WL, Basic, EN16931 (that profile corresponds to the EU standard of the same name) and Extended.

================
About Chorus Pro
================

`Chorus Pro <https://chorus-pro.gouv.fr/>`_ is the e-invoicing portal of the French administration. Starting January 1st 2020, all companies that invoice a public entity (State, local administrations, hospitals, etc.) must send their invoice through Chorus Pro (cf `this page from the Ministry of Economy website <https://www.economie.gouv.fr/entreprises/marches-publics-facture-electronique>`_. Chorus Pro accepts electronic invoices in Factur-X format in any of the 5 profiles. Chorus Pro also accepts electronic invoices in standards other than Factur-X.
