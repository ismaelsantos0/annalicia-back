import re
import base64
import requests
import json
from bs4 import BeautifulSoup

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
}

def extract_shortcode(url: str) -> str:
    match = re.search(r'instagram\.com/(?:p|reel|tv)/([^/?#]+)', url)
    if not match:
        raise ValueError(
            "Link inválido. Use o link de uma publicação, ex: https://www.instagram.com/p/XXXXXX/"
        )
    return match.group(1)

def image_url_to_base64(img_url: str) -> str:
    resp = requests.get(img_url, timeout=20, headers=_HEADERS)
    resp.raise_for_status()
    content_type = resp.headers.get("Content-Type", "image/jpeg").split(";")[0]
    b64 = base64.b64encode(resp.content).decode("utf-8")
    return f"data:{content_type};base64,{b64}"

def _try_oembed(url: str) -> dict | None:
    """Tenta pegar imagem via oEmbed público do Instagram."""
    try:
        r = requests.get(
            "https://api.instagram.com/oembed/",
            params={"url": url, "maxwidth": 800},
            headers=_HEADERS,
            timeout=10
        )
        if r.ok:
            data = r.json()
            return {
                "thumbnail_url": data.get("thumbnail_url"),
                "caption": data.get("title", ""),
            }
    except Exception:
        pass
    return None

def _try_embed_page(shortcode: str) -> list[str]:
    """
    Busca imagens parseando a página de embed público do Instagram.
    Funciona para posts públicos sem precisar de login.
    """
    embed_url = f"https://www.instagram.com/p/{shortcode}/embed/captioned/"
    r = requests.get(embed_url, headers=_HEADERS, timeout=15)
    r.raise_for_status()

    html = r.text
    image_urls = []

    # Tenta achar imagens em blocos JSON embutidos na página
    json_matches = re.findall(r'"display_url"\s*:\s*"([^"]+)"', html)
    if json_matches:
        for raw_url in json_matches:
            clean = raw_url.replace("\\u0026", "&").replace("\\/", "/")
            image_urls.append(clean)
        return list(dict.fromkeys(image_urls))  # remove duplicatas mantendo ordem

    # Fallback: parsear tags <img> da página de embed
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if "cdninstagram.com" in src or "fbcdn.net" in src:
            image_urls.append(src)

    return list(dict.fromkeys(image_urls))

def fetch_instagram_post(url: str) -> dict:
    shortcode = extract_shortcode(url)
    caption = ""
    images_b64 = []

    # Tenta 1: página de embed
    try:
        img_urls = _try_embed_page(shortcode)
        if img_urls:
            for img_url in img_urls[:8]:
                try:
                    images_b64.append(image_url_to_base64(img_url))
                except Exception:
                    pass
    except Exception as e:
        pass

    # Tenta 2: oEmbed (fallback com 1 imagem)
    if not images_b64:
        oembed = _try_oembed(url)
        if oembed and oembed.get("thumbnail_url"):
            try:
                images_b64.append(image_url_to_base64(oembed["thumbnail_url"]))
                caption = oembed.get("caption", "")
            except Exception:
                pass

    if not images_b64:
        raise ValueError(
            "Não foi possível acessar as imagens deste post. Verifique se o perfil é público e tente novamente."
        )

    # Nome sugerido: primeira linha não vazia da legenda
    nome_sugerido = ""
    for linha in caption.split("\n"):
        linha_clean = re.sub(r'[#@]\S+', '', linha).strip()
        linha_clean = re.sub(r'[^\w\s]', '', linha_clean).strip()
        if len(linha_clean) > 2:
            nome_sugerido = linha_clean[:80]
            break

    return {
        "images": images_b64,
        "caption": caption,
        "nome_sugerido": nome_sugerido,
    }
