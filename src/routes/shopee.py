from flask import Blueprint, request, jsonify
import pandas as pd
import io
import base64
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

shopee_bp = Blueprint('shopee', __name__)

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
        
        # Processar o CSV (similar ao script anterior)
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
        
        # Remover linhas com valores inválidos
        df.dropna(subset=['TITULO_PRODUTO', 'PRECO_ORIGINAL', 'PRECO_PROMOCIONAL', 'LINK_PRODUTO'], inplace=True)
        
        # Processar todos os produtos (removido filtro de desconto mínimo)
        df_filtered = df.copy()
        
        # Ordenar por desconto (se existir)
        if 'PERCENTUAL_DESCONTO' in df_filtered.columns:
            df_filtered = df_filtered.sort_values(by='PERCENTUAL_DESCONTO', ascending=False)
        
        # Limitar a 500 produtos para não sobrecarregar a interface
        df_filtered = df_filtered.head(500)
        
        # Converter para lista de dicionários, preenchendo NaN com valores padrão e garantindo tipos JSON-compatíveis
        df_filtered = df_filtered.fillna({
            'TITULO_PRODUTO': '',
            'DESCRICAO_PRODUTO': '',
            'URL_IMAGEM': '',
            'PRECO_ORIGINAL': 0.0,
            'PRECO_PROMOCIONAL': 0.0,
            'PERCENTUAL_DESCONTO': 0.0,
            'LINK_PRODUTO': ''
        })
        
        # Converter colunas numéricas para float padrão para garantir compatibilidade com JSON
        for col in ['PRECO_ORIGINAL', 'PRECO_PROMOCIONAL', 'PERCENTUAL_DESCONTO']:
            df_filtered[col] = df_filtered[col].astype(float)

        # Converter DataFrame para JSON, tratando NaNs explicitamente para None
        products = df_filtered.replace({pd.NA: None, pd.NaT: None, float('nan'): None}).to_dict('records')
        
        return jsonify({
            'success': True,
            'products': products,
            'total': len(products)
        })
        
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
        cupom = data.get('cupom', '').strip()  # Campo de cupom personalizado
        
        # Função para gerar imagem em um formato específico
        def generate_image_format(width, height):
            img = Image.new('RGB', (width, height), color='#000000')  # Fundo preto
            draw = ImageDraw.Draw(img)
            
            # Tentar carregar fonte personalizada (fallback para fonte padrão)
            try:
                title_font = ImageFont.truetype("static/fonts/DejaVuSans-Bold.ttf", int(48 * width / 1080))
                desc_font = ImageFont.truetype("static/fonts/DejaVuSans.ttf", int(32 * width / 1080))
                price_font = ImageFont.truetype("static/fonts/DejaVuSans-Bold.ttf", int(56 * width / 1080))
                small_font = ImageFont.truetype("static/fonts/DejaVuSans.ttf", int(24 * width / 1080))
            except:
                title_font = ImageFont.load_default()
                desc_font = ImageFont.load_default()
                price_font = ImageFont.load_default()
                small_font = ImageFont.load_default()
            
            # Cabeçalho com linha dourada
            header_height = int(100 * height / 1080)
            draw.rectangle([(0, 0), (width, header_height)], fill='#000000')
            draw.line([(int(width * 0.1), header_height - 5), (int(width * 0.9), header_height - 5)], fill='#ffd700', width=3)
            draw.text((width//2, header_height//2), "ESCOLHASHOP", font=title_font, fill='white', anchor='mm')
            
            # Título do produto
            y_pos = header_height + int(50 * height / 1080)
            lines = []
            words = title.split()
            current_line = ""
            
            for word in words:
                test_line = current_line + " " + word if current_line else word
                bbox = draw.textbbox((0, 0), test_line, font=title_font)
                if bbox[2] - bbox[0] <= width - int(40 * width / 1080):
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            
            for line in lines[:2]:  # Máximo 2 linhas para o título
                draw.text((width//2, y_pos), line, font=title_font, fill='white', anchor='mm')
                y_pos += int(60 * height / 1080)
            
            # Imagem do produto (maior)
            product_img_y = y_pos + int(30 * height / 1080)
            max_img_size = int(450 * min(width, height) / 1080)  # Imagem maior
            
            if image_url:
                try:
                    response = requests.get(image_url, timeout=30)
                    product_img = Image.open(BytesIO(response.content))
                    product_img = product_img.convert("RGB")
                    print(f"Image downloaded successfully from {image_url}")
                    
                    # Redimensionar mantendo proporção
                    product_img.thumbnail((max_img_size, max_img_size), Image.Resampling.LANCZOS)
                    print(f"Image resized to {product_img.width}x{product_img.height}")
                    
                    # Criar fundo branco arredondado para a imagem
                    bg_size = max_img_size + int(40 * width / 1080)
                    bg_img = Image.new('RGBA', (bg_size, bg_size), (255, 255, 255, 255))
                    
                    # Centralizar imagem do produto no fundo branco
                    img_x_offset = (bg_size - product_img.width) // 2
                    img_y_offset = (bg_size - product_img.height) // 2
                    bg_img.paste(product_img, (img_x_offset, img_y_offset))
                    
                    # Centralizar o conjunto na imagem principal
                    bg_x = (width - bg_size) // 2
                    bg_y = product_img_y
                    img.paste(bg_img, (bg_x, bg_y))
                    print("Image pasted onto ad template")
                    
                    y_pos = bg_y + bg_size + int(30 * height / 1080)
                except Exception as e:
                    print(f"Error loading or processing image {image_url}: {e}")
                    # Placeholder se não conseguir carregar a imagem
                    placeholder_size = max_img_size
                    draw.rectangle([(width//2 - placeholder_size//2, product_img_y), 
                                   (width//2 + placeholder_size//2, product_img_y + placeholder_size)], 
                                   fill='white')
                    draw.text((width//2, product_img_y + placeholder_size//2), "Imagem\ndo Produto", 
                             font=desc_font, fill='black', anchor='mm')
                    y_pos = product_img_y + placeholder_size + int(30 * height / 1080)
            
            # Descrição do produto (REMOVIDA conforme solicitação)
            # A descrição não aparecerá mais na imagem
            
            # Preços
            if original_price > 0:
                price_text = f"De: R$ {original_price:.2f}".replace('.', ',')
                # Desenhar texto riscado
                bbox = draw.textbbox((0, 0), price_text, font=desc_font)
                text_width = bbox[2] - bbox[0]
                text_x = width//2 - text_width//2
                draw.text((width//2, y_pos), price_text, font=desc_font, fill='#888888', anchor='mm')
                # Linha riscando o preço
                draw.line([(text_x, y_pos), (text_x + text_width, y_pos)], fill='#888888', width=2)
                y_pos += int(50 * height / 1080)
            
            # Preço promocional
            draw.text((width//2, y_pos), f"POR R$ {promo_price:.2f}".replace('.', ','), 
                     font=price_font, fill='#ffd700', anchor='mm')
            y_pos += int(80 * height / 1080)
            
            # Desconto (se houver)
            if discount > 0:
                draw.text((width//2, y_pos), f"{discount:.0f}% OFF", 
                         font=title_font, fill='#ff3c00', anchor='mm')
                y_pos += int(60 * height / 1080)
            
            # Cupom personalizado (se fornecido)
            if cupom and y_pos < height - int(100 * height / 1080):
                # Desenhar caixa do cupom com borda pontilhada
                cupom_y = y_pos + int(20 * height / 1080)
                cupom_width = int(250 * width / 1080)  # Largura maior para acomodar texto personalizado
                cupom_height = int(60 * height / 1080)
                cupom_x = width//2 - cupom_width//2
                
                # Simular borda pontilhada
                for i in range(0, cupom_width, 10):
                    draw.line([(cupom_x + i, cupom_y), (cupom_x + min(i + 5, cupom_width), cupom_y)], fill='#ffd700', width=2)
                    draw.line([(cupom_x + i, cupom_y + cupom_height), (cupom_x + min(i + 5, cupom_width), cupom_y + cupom_height)], fill='#ffd700', width=2)
                
                for i in range(0, cupom_height, 10):
                    draw.line([(cupom_x, cupom_y + i), (cupom_x, cupom_y + min(i + 5, cupom_height))], fill='#ffd700', width=2)
                    draw.line([(cupom_x + cupom_width, cupom_y + i), (cupom_x + cupom_width, cupom_y + min(i + 5, cupom_height))], fill='#ffd700', width=2)
                
                draw.text((cupom_x + cupom_width//2, cupom_y + 15), "CUPOM:", font=small_font, fill='#ffd700', anchor='mm')
                draw.text((cupom_x + cupom_width//2, cupom_y + 40), cupom.upper(), font=small_font, fill='white', anchor='mm')
            
            return img
        
        # Gerar imagens nos dois formatos
        img_1080x1080 = generate_image_format(1080, 1080)
        img_1080x1920 = generate_image_format(1080, 1920)
        
        # Converter imagens para base64
        buffer_1080 = BytesIO()
        img_1080x1080.save(buffer_1080, format='PNG')
        img_str_1080 = base64.b64encode(buffer_1080.getvalue()).decode()
        
        buffer_1920 = BytesIO()
        img_1080x1920.save(buffer_1920, format='PNG')
        img_str_1920 = base64.b64encode(buffer_1920.getvalue()).decode()
        
        print(f"Generated 1080x1080 image size: {len(img_str_1080)} bytes")
        print(f"Generated 1080x1920 image size: {len(img_str_1920)} bytes")
        
        # Gerar texto para postagem
        post_text = f"🔥 {title} 🔥\n\n"
        if description:
            post_text += f"{description}\n\n"
        if original_price > 0:
            post_text += f"De: R$ {original_price:.2f}\n".replace(".", ",")
        post_text += f"Por: R$ {promo_price:.2f}\n\n".replace(".", ",")
        if discount > 0:
            post_text += f"💥 {discount:.0f}% de desconto!\n\n"
        post_text += f"🛒 Compre Aqui!👇🏻\n{product_link}"
        print(f"Generated post text length: {len(post_text)} characters")
        
        return jsonify({
            'success': True,
            'image_1080x1080': f"data:image/png;base64,{img_str_1080}",
            'image_1080x1920': f"data:image/png;base64,{img_str_1920}",
            'post_text': post_text
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
