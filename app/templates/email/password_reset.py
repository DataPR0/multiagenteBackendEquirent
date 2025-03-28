from urllib.parse import urlparse
from app.config import settings

import html


template = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Restablecimiento de Contraseña</title>
    <style>
        :root {
            --primary-blue: #0E5D9D;
            --secondary-blue: #2EA8E0;
            --white: #FFFFFF;
            --gray-light: #f8f9fa;
            --gray-medium: #E5E5E5;
            --gray-dark: #666;
        }
        
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: var(--gray-dark);
            margin: 0;
            padding: 0;
            background-color: var(--gray-light);
        }
        
        .collaboration-container {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 20px;
        }
        
        .collaboration-x {
            font-size: 24px;
            font-weight: bold;
            color: #0E5D9D;
        }
    </style>
</head>
<body style="background-color: #f8f9fa; padding: 20px;">
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="max-width: 600px; margin: 0 auto;">
        <tr>
            <td style="text-align: center; padding: 40px;">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="width: 100%;">
                    <tr>
                        <td style="width: 45%; text-align: right;">
                            <img src="cid:logo" alt="Equirent Logo" style="width: auto; height: 45px; display: inline-block;">
                        </td>
                        <td style="width: 10%; text-align: center; vertical-align: middle;">
                            <span style="display: inline-block; font-size: 28px; font-weight: bold; color: #0E5D9D; line-height: 45px;">×</span>
                        </td>
                        <td style="width: 45%; text-align: left;">
                            <img src="cid:logo2" alt="Partner Logo" style="width: auto; height: 45px; display: inline-block;">
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 2px 4px rgba(14, 93, 157, 0.1);">
        <tr>
            <td style="padding: 40px 30px;">
                <h1 style="color: #0E5D9D; font-size: 24px; margin-bottom: 20px; text-align: center;">Solicitud de Restablecimiento de Contraseña</h1>
                <p style="margin-bottom: 20px; color: #666;">Hola,</p>
                <p style="margin-bottom: 20px; color: #666;">Hemos recibido una solicitud para restablecer tu contraseña. Si no realizaste esta solicitud, puedes ignorar este correo electrónico.</p>
                <p style="margin-bottom: 20px; color: #666;">Para restablecer tu contraseña, haz clic en el botón a continuación:</p>
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin: 0 auto;">
                    <tr>
                        <td style="border-radius: 8px; background-color: #0E5D9D;">
                            <a href="{{ reset_link }}" target="_blank" style="border: solid 1px #0E5D9D; border-radius: 8px; color: #ffffff; display: inline-block; font-size: 16px; font-weight: bold; padding: 12px 24px; text-decoration: none; text-align: center;">Restablecer Contraseña</a>
                        </td>
                    </tr>
                </table>
                <p style="margin-top: 30px; color: #666;">Si el botón no funciona, también puedes copiar y pegar el siguiente enlace en tu navegador:</p>
                <p style="word-break: break-all; color: #2EA8E0;">{{ reset_link }}</p>
                <p style="margin-top: 30px; color: #666;">Este enlace expirará en 24 horas por razones de seguridad.</p>
                <p style="margin-top: 30px; color: #666;">Si no solicitaste un restablecimiento de contraseña, ignora este correo o contacta a nuestro equipo de soporte si tienes alguna preocupación.</p>
                <p style="margin-top: 30px; color: #666;">Atentamente,<br>Equipo Equirent</p>
            </td>
        </tr>
    </table>
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="max-width: 600px; margin: 20px auto 0; background-color: #f8f9fa; border-radius: 12px; box-shadow: 0 2px 4px rgba(14, 93, 157, 0.1);">
        <tr>
            <td style="padding: 20px; font-size: 12px; color: #666; text-align: justify;">
                <p style="margin-bottom: 10px;">Este mensaje y los anexos pueden contener información confidencial o legalmente protegida y no puede ser utilizada ni divulgada por personas y/o entidades diferentes a su destinatario. Si el lector de este mensaje no fuera el destinatario, considérese por este medio informado de que la retención, difusión, o copia de este correo electrónico está estrictamente prohibida. Si este es el caso, por favor informe de ello al remitente y elimine el mensaje de inmediato, de tal manera que no pueda acceder a él de nuevo.</p>
                <p style="margin-bottom: 10px;">Las opiniones contenidas en este mensaje electrónico no relacionadas con la actividad de Equirent , no necesariamente representan la opinión de la Compañía. Equirent Vehículos y Maquinaria SAS, Equirent SA, Equirent Blindados LTDA, CasaToro Rental SAS no se hace responsable en caso de que en este mensaje o en los archivos adjuntos haya presencia de algún virus que pueda generar daños en los equipos o programas del destinatario. El uso de este correo es exclusivamente para uso interno en Equirent Vehículos y Maquinaria SAS, Equirent SA, Equirent Blindados LTDA, CasaToro Rental SAS y no está creado para efectos de comunicaciones formales de la Compañía hacia terceros, por lo que el contenido de este correo no obliga ni vincula de manera alguna a Equirent Vehículos y Maquinaria SAS, Equirent SA, Equirent Blindados LTDA, CasaToro Rental SAS.</p>
                <p style="margin-bottom: 0;">Aviso Importante: Las anteriores compañías tratarán la información de conformidad con los principios y disposiciones contenidas en la Ley 1266 de 2008, 1581 de 2012 y el Decreto 1377 del 2013.</p>
            </td>
        </tr>
    </table>
</body>
</html>
"""


def get_template(reset_link: str) -> str:
    """
    Returns a password reset template with the provided reset link injected into it.
    
    The reset link is validated to ensure it has a valid scheme (http or https) and 
    a netloc that matches the frontend URL. If the link is invalid, None is returned.
    
    Args:
    reset_link (str): The password reset link to be injected into the template.
    
    Returns:
    str: The password reset template with the reset link injected, or None if the link is invalid.
    """
    # Validate reset link before injecting it into the template
    safe_reset_link = html.escape(reset_link)
    parsed_reset_url = urlparse(safe_reset_link)
    parsed_front_url = urlparse(settings.front_url)
    if not (parsed_reset_url.scheme in ('http', 'https') and parsed_reset_url.netloc == parsed_front_url.netloc):
        return None
    return template.replace("{{ reset_link }}", safe_reset_link)
