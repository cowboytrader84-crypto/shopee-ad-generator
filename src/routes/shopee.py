from flask import Blueprint, request, jsonify
import pandas as pd
import io
import base64
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import os

shopee_bp = Blueprint('shopee', __name__)

# Definir caminho absoluto para a pasta de fontes
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS_DIR = os.path.join(BASE_DIR, "static", "fonts")

@shopee_bp.route('/upload-csv', methods=['POST'])
def upload_csv():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
        
        # Ler o CSV
        df = pd.read_csv(file)
        
        # Processar o CSV
        df = df.rename(columns={
            'image_link': 'URL_IMAGEM',
            'title': 'TITULO_PRODUTO',
            'description': 'DESCRICAO_PRODUTO',
            'price': 'PRECO_ORIGINAL',
            'sale_price': 'PRECO_PROMOCIONAL',
            'discount_percentage': 'PERCENTUAL_DESCONTO',
            'product_link': 'LINK_PRODUTO'
        })
        
        # Converter colunas para numérico
        df['PRECO_ORIGINAL'] = pd.to_numeric(df['PRECO_ORIGINAL'], errors='coerce')
        df['PRECO_PROMOCIONAL'] = pd.to_numeric(df['PRECO_PROMOCIONAL'], errors='coerce')
        df['PERCENTUAL_DESCONTO'] = pd.to_numeric(df['PERCENTUAL_DESCONTO'], errors='coerce')
        
        # Remover linhas inválidas
        df.dropna(subset=['TITULO_PRODUTO', 'PRECO_ORIGINAL', 'PRECO_PROMOCIONAL', 'LINK_PRODUTO'], inplace=True)
        
        # Ordenar por desconto
        df_filtered = df.copy()
        if 'PERCENTUAL_DESCONTO' in df_filtered.columns:
            df_filtered = df_filtered.sort_values(by='PERCENTUAL_DESCONTO', ascending=False)
        
        # Limitar a 500 produtos
        df_filtered = df_filtered.head(500)
        
        # Preencher valores nulos
        df_filtered = df_filtered.fillna({
            'TITULO_PRODUTO': '',
            'DESCRICAO_PRODUTO': '',
            'URL_IMAGEM': '',
            'PRECO_ORIGINAL': 0.0,
            'PRECO_PROMOCIONAL': 0.0,
            'PERCENTUAL_DESCONTO': 0.0,
            'LINK_PRODUTO': ''
        })
        
        # Garantir float
        for col in ['PRECO_ORIGINAL', 'PRECO_PROMOCIONAL', 'PERCENTUAL_DESCONTO']:
            df_filtered[col] = df_filtered[col].astype(float)

        products = df_filtered.replace({pd.NA: None, pd.NaT: None, float('nan'): None}).to_dict('records')
        
        return jsonify({'success': True, 'products': products, 'total': len(products)})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@shopee_bp.route('/generate-ad', methods=['POST'])
def generate_ad():
    try:
        data = request.json
        
        # Extrair dados do produto
        title = data.get('title', '')
        description = data.get('description', '')[:200] + '...' if len(data.get('description', '')) > 200 else data.get('description', '')
        image_url = data.get('image_url', '')
        original_price = data.get('original_price', 0)
        promo_price = data.get('promo_price', 0)
        discount = data.get('discount', 0)
        product_link = data.get('product_link', '')
        cupom = data.get('cupom', '').strip()
        
        def generate_image_format(width, height):
            img = Image.new('RGB', (width, height), color='#000000')
            draw = ImageDraw.Draw(img)
            
            # Carregar fontes locais
            try:
                title_font = ImageFont.truetype(os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf"), int(48 * width / 1080))
                desc_font = ImageFont.truetype(os.path.join(FONTS_DIR, "DejaVuSans.ttf"), int(32 * width / 1080))
                price_font = ImageFont.truetype(os.path.join(FONTS_DIR, "DejaVuSans-Bold.ttf"), int(56 * width / 1080))
                small_font = ImageFont.truetype(os.path.join(FONTS_DIR, "DejaVuSans.ttf"), int(24 * width / 1080))
            except Exception as e:
                print(f"Erro ao carregar fontes: {e}")
                title_font = ImageFont.load_default()
                desc_font = ImageFont.load_default()
                price_font = ImageFont.load_default()
                small_font = ImageFont.load_default()
            
            # Cabeçalho
            header_height = int(100 * height / 1080)
            draw.rectangle([(0, 0), (width, header_height)], fill='#000000')
            draw.line([(int(width * 0.1), header_height - 5), (int(width * 0.9), header_height - 5)], fill='#ffd700', width=3)
            draw.text((width//2, header_height//2), "ESCOLHASHOP", font=title_font, fill='white', anchor='mm')
            
            # (restante do código do generate_image_format continua igual ao seu)
            # ...
            
            return img
        
        # Gerar imagens
        img_1080x1080 = generate_image_format(1080, 1080)
        img_1080x1920 = generate_image_format(1080, 1920)
        
        # Converter para base64
        buffer_1080 = BytesIO()
        img_1080x1080.save(buffer_1080, format='PNG')
        img_str_1080 = base64.b64encode(buffer_1080.getvalue()).decode()
        
        buffer_1920 = BytesIO()
        img_1080x1920.save(buffer_1920, format='PNG')
        img_str_1920 = base64.b64encode(buffer_1920.getvalue()).decode()
        
        post_text = f"🔥 {title} 🔥\n\n"
        if description:
            post_text += f"{description}\n\n"
        if original_price > 0:
            post_text += f"De: R$ {original_price:.2f}\n".replace(".", ",")
        post_text += f"Por: R$ {promo_price:.2f}\n\n".replace(".", ",")
        if discount > 0:
            post_text += f"💥 {discount:.0f}% de desconto!\n\n"
        post_text += f"🛒 Compre Aqui!👇🏻\n{product_link}"
        
        return jsonify({
            'success': True,
            'image_1080x1080': f"data:image/png;base64,{img_str_1080}",
            'image_1080x1920': f"data:image/png;base64,{img_str_1920}",
            'post_text': post_text
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
