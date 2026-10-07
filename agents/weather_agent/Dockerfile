FROM public.ecr.aws/docker/library/python:3.12-slim

WORKDIR /app
ARG PIP_INDEX_URL
COPY agents/weather_agent/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && addgroup --system agentcore \
    && adduser --system --ingroup agentcore agentcore
COPY agents/common ./agents/common
COPY agents/weather_agent ./agents/weather_agent
RUN chown -R agentcore:agentcore /app
USER agentcore
ENV PYTHONUNBUFFERED=1
EXPOSE 9000
CMD ["python", "-m", "agents.weather_agent.main"]
