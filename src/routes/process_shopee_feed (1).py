
import pandas as pd

def process_shopee_feed(file_path, min_discount=0):
    df = pd.read_csv(file_path)

    # Renomear colunas para facilitar o acesso
    df = df.rename(columns={
        'image_link': 'URL_IMAGEM',
        'title': 'TITULO_PRODUTO',
        'description': 'DESCRICAO_PRODUTO',
        'price': 'PRECO_ORIGINAL',
        'sale_price': 'PRECO_PROMOCIONAL',
        'discount_percentage': 'PERCENTUAL_DESCONTO',
        'product_link': 'LINK_PRODUTO'
    })

    # Converter colunas de preço para numérico, tratando erros
    df['PRECO_ORIGINAL'] = pd.to_numeric(df['PRECO_ORIGINAL'], errors='coerce')
    df['PRECO_PROMOCIONAL'] = pd.to_numeric(df['PRECO_PROMOCIONAL'], errors='coerce')
    df['PERCENTUAL_DESCONTO'] = pd.to_numeric(df['PERCENTUAL_DESCONTO'], errors='coerce')

    # Remover linhas com valores inválidos nas colunas essenciais
    df.dropna(subset=['TITULO_PRODUTO', 'PRECO_ORIGINAL', 'PRECO_PROMOCIONAL', 'LINK_PRODUTO'], inplace=True)

    # Filtrar produtos com desconto maior ou igual ao mínimo especificado
    df_filtered = df[df['PERCENTUAL_DESCONTO'] >= min_discount].copy()

    # Ordenar por percentual de desconto (maior para menor)
    df_filtered = df_filtered.sort_values(by='PERCENTUAL_DESCONTO', ascending=False)

    # Selecionar apenas as colunas desejadas para a saída
    output_columns = [
        'TITULO_PRODUTO',
        'DESCRICAO_PRODUTO',
        'URL_IMAGEM',
        'PRECO_ORIGINAL',
        'PRECO_PROMOCIONAL',
        'PERCENTUAL_DESCONTO',
        'LINK_PRODUTO'
    ]

    return df_filtered[output_columns]

if __name__ == '__main__':
    input_file = '/home/ubuntu/upload/1005_200149_ShopeeBrasil-2022_20250820T050219_1.csv'
    output_file = 'shopee_ofertas_filtradas.csv'
    min_discount_percentage = 20 # Defina o percentual mínimo de desconto desejado

    processed_df = process_shopee_feed(input_file, min_discount=min_discount_percentage)

    if not processed_df.empty:
        processed_df.to_csv(output_file, index=False)
        print(f"Dados processados e salvos em '{output_file}'.")
        print(f"Total de ofertas filtradas com desconto >= {min_discount_percentage}%: {len(processed_df)}")
    else:
        print("Nenhuma oferta encontrada com os critérios especificados.")


