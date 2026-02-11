FROM python:3.10-slim
LABEL "language"="python"
LABEL "framework"="flask"

WORKDIR /src

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

CMD ["sh", "-c", "cd src && python -c \"import app; app.app.run(host='0.0.0.0', port=8080, debug=False)\""]
