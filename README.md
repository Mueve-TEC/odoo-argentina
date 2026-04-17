# Odoo Argentina

Localización Argentina para Odoo Community Edition 18. Esta versión está basada en los desarrollos de
[Ingeniería ADHOC](https://github.com/ingadhoc) y cuenta con los módulos, en el directorio `adhoc-modules`, de los siguientes repositorios:

- [odoo-argentina](https://github.com/ingadhoc/odoo-argentina/tree/18.0)
- [odoo-argentina-ce](https://github.com/ingadhoc/odoo-argentina-ce/tree/18.0)
- [account-payment](https://github.com/ingadhoc/account-payment/tree/18.0)
- [account-financial-tools](https://github.com/ingadhoc/account-financial-tools/tree/18.0)

Además, en el directorio `mueve-modules` se incluye los módulos desarrollados por Mueve.

## PyAFIPws

Para poder utilizar los módulos que se conectan con los web services del ARCA (ex AFIP), se necesita tener instalada la versión actualizada de la libreria de Python 3 ***pyafipws*** (rama `py3k`) que se encuentra en: **<https://github.com/Mueve-TEC/pyafipws/tree/py3k>**

Para instalar esta libreria y el resto de dependencias puede usar el [requirements.txt](/requirements.txt) que se encuentra en el repositorio.

Instalación con pip de los requirements:

```bash
pip install -r requirements.txt
```
