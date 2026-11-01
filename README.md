# Madeleine Coiffeur

Site com o painel do Instagram do Madeleine Coiffeur e as análises.

- Painel do Instagram: página inicial
- Análise 2026: `/analise`

Os números do Instagram são atualizados sozinhos às 6h, 12h e 18h (horário de Brasília) pelo robô em `.github/workflows/atualizar.yml`, que busca os dados no Windsor.ai com o segredo `WINDSOR_API_KEY`.

Para atualizar na hora: aba **Actions** → **Atualizar dados do Instagram** → **Run workflow**.
