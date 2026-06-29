import instaloader
import requests
import base64
import re
import tempfile
import os
from pathlib import Path

_loader = instaloader.Instaloader(
    download_pictures=False,
    download_videos=False,
    download_video_thumbnails=False,
    download_geotags=False,
    download_comments=False,
    save_metadata=False,
    compress_json=False,
    quiet=True
)

def extract_shortcode(url: str) -> str:
    """Extrai o shortcode do post do Instagram a partir da URL."""
    # Ex: https://www.instagram.com/p/ABC123/ ou https://instagram.com/reel/ABC123/
    match = re.search(r'instagram\.com/(?:p|reel|tv)/([^/?#]+)', url)
    if not match:
        raise ValueError("Link do Instagram inválido. Use o link de uma publicação, ex: https://www.instagram.com/p/XXXXXX/")
    return match.group(1)

def image_url_to_base64(url: str) -> str:
    """Baixa uma imagem de uma URL e converte para base64 webp."""
    resp = requests.get(url, timeout=15, headers={
        "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1)"
    })
    resp.raise_for_status()
    content_type = resp.headers.get("Content-Type", "image/jpeg")
    b64 = base64.b64encode(resp.content).decode("utf-8")
    return f"data:{content_type};base64,{b64}"

def fetch_instagram_post(url: str) -> dict:
    """
    Usa instaloader para buscar dados de um post público do Instagram.
    Retorna dict com 'images' (lista de base64) e 'caption'.
    """
    shortcode = extract_shortcode(url)
    post = instaloader.Post.from_shortcode(_loader.context, shortcode)

    images = []
    caption = post.caption or ""

    if post.typename == "GraphSidecar":
        # Post com múltiplas imagens (carrossel)
        for node in post.get_sidecar_nodes():
            if not node.is_video:
                img_b64 = image_url_to_base64(node.display_url)
                images.append(img_b64)
                if len(images) >= 8:
                    break
    elif not post.is_video:
        # Post de imagem simples
        img_b64 = image_url_to_base64(post.url)
        images.append(img_b64)

    # Nome sugerido: primeira linha não vazia da legenda
    nome_sugerido = ""
    for linha in caption.split("\n"):
        linha = linha.strip()
        # Remove emojis e símbolos comuns em legendas de moda
        linha_clean = re.sub(r'[#@][\w]+', '', linha).strip()
        if len(linha_clean) > 2:
            nome_sugerido = linha_clean[:80]
            break

    return {
        "images": images,
        "caption": caption,
        "nome_sugerido": nome_sugerido
    }
