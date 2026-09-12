# Serviço de cálculo do Lastro: motor de risco determinístico, dataset simulado,
# camada de linguagem natural e a camada de coleta de fontes públicas.
#
# Roda com WORKER ÚNICO de propósito: o ledger de custo do LLM é estado em
# memória do processo, e vários workers dividiriam o teto de gasto. Ver o
# cabeçalho de api/app.py.

FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependências primeiro, para a camada de cache do Docker sobreviver a mudança de código.
# São dois arquivos: o do serviço de risco e o da camada de coleta.
COPY api/requirements.txt /tmp/requirements-api.txt
COPY requirements.txt /tmp/requirements-coleta.txt
RUN pip install -r /tmp/requirements-api.txt -r /tmp/requirements-coleta.txt

# O serviço roda com /app/api como raiz de import (é assim que `flask --app app`
# resolve `models`, `scoring`, `data`, `llm`), e `coleta` fica importável ao lado.
COPY api/ /app/api/
COPY coleta/ /app/coleta/

ENV PYTHONPATH=/app:/app/api \
    FLASK_APP=app \
    PORT=5001 \
    LASTRO_LLM_MODEL=gpt-5.4-mini \
    LASTRO_LLM_ENABLED=true \
    LASTRO_LLM_BUDGET_USD=8

WORKDIR /app/api

EXPOSE 5001

# Sem --debug: o reloader do Flask duplicaria o processo e, com ele, o ledger.
CMD ["python", "-m", "flask", "--app", "app", "run", "--host", "0.0.0.0", "--port", "5001"]
