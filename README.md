| Metric Name                     | Description                           | Labels           |
| ------------------------------- | ------------------------------------- | ---------------- |
| `http_requests_total`           | Number of HTTP requests               | method, endpoint |
| `http_request_duration_seconds` | Request latency in seconds            | endpoint         |
| `model_calls_total`             | Number of model invocations           | model            |
| `upload_success_total`          | Number of successful document uploads | file\_type       |
| `upload_fail_total`             | Number of failed document uploads     | file\_type       |
| `new_sessions_total`            | Number of new chat sessions created   | —                |


```bash
# check files inside the docker image
docker run -it --entrypoint /bin/sh rag-app

docker run -it --entrypoint /bin/bash rag-app

docker run -it --entrypoint sh mera_appication-coin-api

docker inspect mera_appication-coin-api


ls -al /
ls -al /app
cat /app/app.py


## Always do not create the docker image with .env file/ secret files
# Build the image
docker build -t rag-app .
# Run the container and inject environment variables at runtime

docker run -p 8000:8000 --env-file .env myrag

docker run -p 8000:8000 -it --entrypoint sh  --env-file .env myrag
```

```bash
# to run docker with env variables
docker run -p 8000:8000 -e GOOGLE_API_KEY=your_google_api -e GROQ_API_KEY= your_groq_key myrag
```
```bash 
# to check the docker cpu/ram usage 
docker stats
```

## Monitoring

#### Application Performance Monitoring (APM)

- **Request tracking**: Total HTTP requests by method and endpoint
- **Latency monitoring**: Request duration histogram to track response times
- **Automatic middleware**: Captures all HTTP requests without manual instrumentation

#### Business Logic Monitoring

- **AI/ML model usage**: Tracks total calls to different language models
- **Document operations**: Monitors successful and - failed document uploads by file type
- **User sessions**: Counts new chat sessions created

#### System Resource Monitoring

- **CPU usage**: Real-time CPU percentage monitoring
- **Memory usage**: RAM utilization percentage
- **Disk usage**: Storage utilization percentage
- **Background collection**: Continuous system metrics collection every 5 seconds

#### Infrastructure Monitoring

- **Prometheus integration**: Standard /metrics endpoint for Prometheus scraping
- **Standardized metrics**: Uses Prometheus client library with proper metric types:

- **Counter for incrementing values**(requests, uploads, sessions)
- **Histogram** for latency distributions
Gauge for current system resource levels