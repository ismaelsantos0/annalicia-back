import re
import unicodedata

def remove_accents_and_special(s: str) -> str:
    if not s:
        return ""
    nfkd_form = unicodedata.normalize('NFKD', s)
    s = u"".join([c for c in nfkd_form if not unicodedata.combining(c)])
    return re.sub(r'[^A-Za-z0-9 ]', '', s)

def crc16(data: str) -> str:
    crc = 0xFFFF
    for byte in data.encode('utf-8'):
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc = crc << 1
            crc &= 0xFFFF
    return f"{crc:04X}"

def generate_pix_brcode(chave: str, tipo: str, nome: str, cidade: str, valor: float, txid: str = "***") -> str:
    """
    Gera um código PIX Copia e Cola estático (BR Code EMVCo).
    """
    if not chave or not nome or not cidade or not valor:
        return ""
        
    def format_len(id_field: str, value: str) -> str:
        return f"{id_field}{len(value):02d}{value}"
    
    # Tratar chave pix de acordo com o tipo
    chave = chave.strip()
    tipo = (tipo or "").lower()
    
    if tipo in ("cpf", "cnpj"):
        chave = re.sub(r'\D', '', chave)
    elif tipo == "telefone":
        chave = re.sub(r'\D', '', chave)
        if len(chave) == 10 or len(chave) == 11:
            chave = f"+55{chave}"
        elif len(chave) > 0 and not chave.startswith("+"):
            chave = f"+{chave}"
    
    gui = format_len("00", "br.gov.bcb.pix")
    key = format_len("01", chave)
    merchant_account = format_len("26", gui + key)
    
    payload = ""
    payload += format_len("00", "01") # Payload Format Indicator
    payload += format_len("01", "11") # Point of Initiation Method
    payload += merchant_account
    payload += format_len("52", "0000") # Merchant Category Code
    payload += format_len("53", "986") # Transaction Currency
    payload += format_len("54", f"{valor:.2f}") # Transaction Amount
    payload += format_len("58", "BR") # Country Code
    
    # Nome e cidade precisam ser limpos e ter limites de caracteres
    nome = remove_accents_and_special(nome)[:25].strip().upper() or "LOJA"
    cidade = remove_accents_and_special(cidade)[:15].strip().upper() or "CIDADE"
    
    payload += format_len("59", nome)
    payload += format_len("60", cidade)
    
    # Aditional Data Field Template
    # Some banks restrict txid characters to alphanumeric only. We use *** if empty or invalid.
    tx_val = re.sub(r'[^A-Za-z0-9]', '', txid)
    if not tx_val:
        tx_val = "***"
    tx_field = format_len("05", tx_val[:25])
    payload += format_len("62", tx_field)
    
    # Checksum (CRC16)
    payload += "6304"
    payload += crc16(payload)
    
    return payload
