# Odoo Argentina

Migración de la Localización Argentina para Odoo Community versión 13. También funcionaría con la versión Enterprise de Odoo.
No funciona con versiones anteriores.

Comprende las siguientes funcionalidades:

- Factura Electrónica
- Cheques
- Recibos para pagos con múltiples medios de pago
- Percepciones
- Retenciones
- Tipo de Cambio Automático

Si tienen algún problema con la localización, por favor crear un Issue en este repositorio. Posteriormente, pueden contactar al desarrollador mediante mail a <gustavo.orrillo@moldeointeractive.com.ar>.
Recordamos que el mail no es para soporte, sino para ponernos al tanto de los posibles problemas que pueda tener la localización.
El link con el roadmap de la localización lo van a encontrar aca:
<https://www.moldeointeractive.com.ar/blog/moldeo-interactive-1/post/roadmap-para-localizacion-argentina-odoo-community-813>

## Instructivo: Configuración de Localización Argentina

[![Localización Argentina Webinar](https://img.youtube.com/vi/BhaBwOMgkIM/maxresdefault.jpg)](https://www.youtube.com/watch?v=BhaBwOMgkIM)

## PyAFIPws

Para poder utilizar los módulos que se conectan con los web services del ARCA (ex AFIP), se necesita tener instalada la versión actualizada de la libreria de Python 3 ***pyafipws*** (rama `py3k`) que se encuentra en: **<https://github.com/Mueve-TEC/pyafipws/tree/py3k>**

Para instalar esta libreria y el resto de dependencias puede usar el [requirements.txt](/requirements.txt) que se encuentra en el repositorio.

Instalación con pip de los requirements:

```bash
pip install -r requirements.txt
```
