FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:1
ENV HOME=/root
ENV GATEWAY_URL=http://host.docker.internal:8000

# 필수 패키지 설치 (Chromium + noVNC + 네트워크 수집)
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    x11vnc \
    novnc \
    websockify \
    supervisor \
    net-tools \
    chromium \
    fonts-liberation \
    fonts-noto-cjk \
    dbus-x11 \
    tcpdump \
    tshark \
    && rm -rf /var/lib/apt/lists/*

# Python 네트워크 에이전트 의존성
RUN pip install --no-cache-dir requests psutil

RUN mkdir -p /dev/shm && chmod 1777 /dev/shm

# 설정 파일 복사
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY start.sh /start.sh
COPY network_agent.py /opt/network_agent.py
RUN chmod +x /start.sh

EXPOSE 6080

CMD ["/start.sh"]
