# Aave Health Factor Simulator

Simulador interativo do Health Factor da posição Aave V4 com colateral WBTC e dívida em stablecoins.

## Como usar

Abra o arquivo `index.html` diretamente no navegador — não requer servidor.

## Funcionalidades

- Slider para simular o Health Factor em qualquer preço de BTC ($40k–$150k)
- Botão "Atualizar preço" que busca o preço atual do Bitcoin via API da Anthropic
- Gráfico de HF × preço com marcador na posição atual
- Indicadores de zona de risco (seguro / risco / liquidação iminente)

## Posição simulada

| Parâmetro | Valor |
|---|---|
| WBTC colateral | 0.5 BTC |
| Dívida total | $20,000.00 (USDG + USDT + USDC) |
| Liquidation Threshold | 78% |
| Preço de liquidação | ~$51,282 |

## Atualização de preço em tempo real

O botão usa a API da Anthropic com web search e só funciona dentro do **claude.ai**.

Não coloque uma chave de API no `index.html`: qualquer pessoa que abrir a página consegue lê-la. Para preço em tempo real fora do claude.ai, use o backend em [`../aave-backend`](../aave-backend), que busca o preço na CoinGecko sem precisar de chave.

## Dependências (CDN)

- Chart.js 4.4.1
- Tabler Icons Webfont 3.19.0
