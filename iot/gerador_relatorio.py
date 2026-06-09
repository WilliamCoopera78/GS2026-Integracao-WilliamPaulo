import os
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
from influxdb_client import InfluxDBClient
from fpdf import FPDF
import requests

INFLUX_URL = "https://us-east-1-1.aws.cloud2.influxdata.com"
INFLUX_TOKEN = "ICXmniQ-TGq6zRWeGSU9VZTCr-u3wejgiLLveQjNfxUJ5Fdm7vnDOZe7TYdPTmGGzRLcM3MKjZkuLNfhRF2RTQ=="
INFLUX_ORG = "FIAP-PROFESSOR"
INFLUX_BUCKET = "agricultura_espacial"

TELEGRAM_BOT_TOKEN = "8292578916:AAFnznRi9bNruEjUpttxRrhwnLDlR3OM98Y"
TELEGRAM_CHAT_ID = "8742849494"

def extrair_dataframe():
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    query = f'''
    from(bucket:"{INFLUX_BUCKET}")
    |> range(start: -1h)
    |> filter(fn: (r) => r._measurement == "telemetria")
    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    '''
    df = client.query_api().query_data_frame(query)
    client.close()
    
    # Valida conversão de múltiplos retornos para DataFrame único
    if isinstance(df, list):
        if len(df) > 0:
            df = pd.concat(df, ignore_index=True)
        else:
            return pd.DataFrame()
            
    return df

def gerar_grafico(df):
    if df.empty or 'temperatura' not in df.columns:
        return None
        
    df = df.sort_values(by='_time')
    
    plt.figure(figsize=(10, 4))
    plt.plot(df['_time'], df['temperatura'], label='Temperatura (°C)', color='#ca3838', linewidth=2)
    plt.plot(df['_time'], df['umidade_ar'], label='Umidade Ar (%)', color='#1f77b4', linewidth=2)
    
    plt.title('Evolucao Temporal - Ultima Hora', fontsize=12, fontweight='bold')
    plt.xlabel('Timestamp')
    plt.ylabel('Valores Absolutos')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    
    caminho_grafico = "plot_telemetria.png"
    plt.savefig(caminho_grafico, dpi=150)
    plt.close()
    return caminho_grafico

def gerar_pdf_avancado(df, caminho_grafico):
    pdf = FPDF()
    pdf.add_page()
    
    # Cabeçalho
    pdf.set_fill_color(40, 44, 52)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 15, "RELATORIO ANALITICO - AGRICULTURA ESPACIAL", ln=True, align='C', fill=True)
    
    # Metadados
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 10)
    pdf.ln(5)
    pdf.cell(0, 5, f"Data de Compilacao: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", ln=True)
    pdf.cell(0, 5, "Operador Tecnico: Gabriel Pessoa", ln=True)
    pdf.ln(10)
    
    if not df.empty:
        # Tabela Estatística
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(230, 230, 230)
        pdf.cell(0, 10, "Resumo Estatistico (Range: 1h):", ln=True, fill=True)
        pdf.set_font("Arial", '', 10)
        
        colunas_alvo = ['temperatura', 'umidade_ar', 'umidade_solo', 'luminosidade']
        for col in colunas_alvo:
            if col in df.columns:
                media = df[col].mean()
                maximo = df[col].max()
                minimo = df[col].min()
                pdf.cell(0, 8, f"- {col.upper()}: Media {media:.2f} | Max {maximo:.2f} | Min {minimo:.2f}", ln=True, border='B')
        
        # Inserção Gráfica
        if caminho_grafico and os.path.exists(caminho_grafico):
            pdf.ln(10)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, "Analise Visual de Parametros Atmosfericos:", ln=True)
            pdf.image(caminho_grafico, x=10, w=190)
            os.remove(caminho_grafico)
    else:
        pdf.cell(0, 10, "Erro: Falha na extracao de dataframe ou base de dados vazia.", ln=True)

    caminho_pdf = "relatorio_telemetria_avancado.pdf"
    pdf.output(caminho_pdf)
    return caminho_pdf

def despachar_telegram(caminho_arquivo):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    with open(caminho_arquivo, 'rb') as arquivo:
        arquivos = {'document': arquivo}
        dados_form = {'chat_id': TELEGRAM_CHAT_ID, 'caption': 'Relatorio Analitico Consolidado.'}
        resposta = requests.post(url, files=arquivos, data=dados_form)
        if resposta.status_code == 200:
            print("Execucao de orquestracao e despacho concluida.")
        else:
            print(f"Falha na API: {resposta.text}")

if __name__ == "__main__":
    df_dados = extrair_dataframe()
    grafico = gerar_grafico(df_dados)
    arquivo_pdf = gerar_pdf_avancado(df_dados, grafico)
    despachar_telegram(arquivo_pdf)