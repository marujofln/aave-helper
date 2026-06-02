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

O botão usa a API da Anthropic com web search. Dentro do **claude.ai** funciona automaticamente.

Para usar **fora do claude.ai**, adicione sua chave de API no cabeçalho da requisição em `fetchPrice()`:

```javascript
headers: {
  'Content-Type': 'application/json',
  'x-api-key': 'SUA_CHAVE_AQUI',
  'anthropic-version': '2023-06-01',
  'anthropic-dangerous-direct-browser-access': 'true'
}
```

Chaves em: https://console.anthropic.com

## Dependências (CDN)

- Chart.js 4.4.1
- Tabler Icons Webfont 3.19.0
