"""
SecureOps 네트워크 수집 에이전트
================================
샌드박스 Docker 컨테이너 안에서 실행.
네트워크 트래픽을 주기적으로 수집하여 Gateway로 전송.
Gateway는 이 데이터를 2번 모델(네트워크 분석)로 포워딩.

수집 데이터 (2번 모델 입력 스펙):
- packet_count: 수집 기간 내 총 패킷 수
- bytes_sent: 송신 바이트
- bytes_received: 수신 바이트
- request_frequency: 초당 요청 수
- unique_domains: 접속한 고유 도메인 수
- dns_query_count: DNS 쿼리 수
- avg_packet_size: 평균 패킷 크기
- protocol_distribution: 프로토콜별 비율 (TCP/UDP/기타)
- connection_count: 활성 연결 수
- suspicious_ports: 비표준 포트 접속 수
"""

import os
import time
import json
import subprocess
import threading
import requests
import psutil
from collections import defaultdict

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://host.docker.internal:8000")
SANDBOX_ID = os.environ.get("SANDBOX_ID", "unknown")
COLLECT_INTERVAL = 5  # 초


class NetworkCollector:
    """네트워크 트래픽 수집기."""

    # 일반적으로 안전한 포트 목록
    STANDARD_PORTS = {80, 443, 53, 8080, 8443}

    def __init__(self):
        self.running = True
        self._prev_net_io = None
        self._prev_time = None
        self._dns_count = 0
        self._packet_buffer = []

    def collect(self) -> dict:
        """현재 네트워크 상태를 수집하여 딕셔너리로 반환."""
        net_io = psutil.net_io_counters()
        connections = psutil.net_connections(kind="inet")
        current_time = time.time()

        # 이전 수집과의 차이 계산
        if self._prev_net_io and self._prev_time:
            elapsed = current_time - self._prev_time
            if elapsed > 0:
                bytes_sent = net_io.bytes_sent - self._prev_net_io.bytes_sent
                bytes_received = net_io.bytes_recv - self._prev_net_io.bytes_recv
                packets_sent = net_io.packets_sent - self._prev_net_io.packets_sent
                packets_recv = net_io.packets_recv - self._prev_net_io.packets_recv
                packet_count = packets_sent + packets_recv
                request_frequency = round(packet_count / elapsed, 2)
            else:
                bytes_sent = bytes_received = packet_count = 0
                request_frequency = 0.0
        else:
            bytes_sent = bytes_received = packet_count = 0
            request_frequency = 0.0

        self._prev_net_io = net_io
        self._prev_time = current_time

        # 활성 연결 분석
        connection_count = 0
        unique_domains = set()
        protocol_counts = defaultdict(int)
        suspicious_port_count = 0

        for conn in connections:
            if conn.status == "ESTABLISHED":
                connection_count += 1

                # 원격 주소 분석
                if conn.raddr:
                    remote_ip = conn.raddr.ip
                    remote_port = conn.raddr.port
                    unique_domains.add(remote_ip)

                    # 비표준 포트 감지
                    if remote_port not in self.STANDARD_PORTS:
                        suspicious_port_count += 1

                # 프로토콜 분류
                if conn.type == 1:  # SOCK_STREAM = TCP
                    protocol_counts["TCP"] += 1
                elif conn.type == 2:  # SOCK_DGRAM = UDP
                    protocol_counts["UDP"] += 1
                else:
                    protocol_counts["OTHER"] += 1

        # 평균 패킷 크기
        total_bytes = bytes_sent + bytes_received
        avg_packet_size = round(total_bytes / packet_count, 2) if packet_count > 0 else 0

        # 프로토콜 비율
        total_conns = sum(protocol_counts.values()) or 1
        protocol_distribution = {
            k: round(v / total_conns, 3) for k, v in protocol_counts.items()
        }

        return {
            "sandbox_id": SANDBOX_ID,
            "timestamp": current_time,
            "packet_count": packet_count,
            "bytes_sent": bytes_sent,
            "bytes_received": bytes_received,
            "request_frequency": request_frequency,
            "unique_domains": len(unique_domains),
            "dns_query_count": self._get_dns_count(),
            "avg_packet_size": avg_packet_size,
            "protocol_distribution": protocol_distribution,
            "connection_count": connection_count,
            "suspicious_ports": suspicious_port_count,
        }

    def _get_dns_count(self) -> int:
        """DNS 쿼리 수 추정 (포트 53 연결 기반)."""
        try:
            conns = psutil.net_connections(kind="inet")
            return sum(1 for c in conns if c.raddr and c.raddr.port == 53)
        except Exception:
            return 0

    def send_to_gateway(self, data: dict):
        """수집된 데이터를 Gateway로 전송."""
        try:
            response = requests.post(
                f"{GATEWAY_URL}/api/sandbox/network-data",
                json=data,
                timeout=5,
            )
            if response.status_code == 200:
                result = response.json()
                if result.get("is_malicious"):
                    print(f"🚨 위협 감지: {result.get('threat_type', 'unknown')}")
        except requests.ConnectionError:
            # Gateway 연결 실패 — 조용히 무시 (다음 주기에 재시도)
            pass
        except Exception as e:
            print(f"⚠️ 데이터 전송 실패: {e}")

    def run(self):
        """메인 루프 — 주기적으로 수집 + 전송."""
        print(f"🔍 네트워크 수집 에이전트 시작 (sandbox: {SANDBOX_ID}, 간격: {COLLECT_INTERVAL}초)")
        print(f"   Gateway: {GATEWAY_URL}")

        # 첫 수집은 기준점 설정용 (전송 안 함)
        self.collect()
        time.sleep(COLLECT_INTERVAL)

        while self.running:
            try:
                data = self.collect()
                self.send_to_gateway(data)

                # 로그 (디버깅용)
                print(
                    f"📡 수집: pkts={data['packet_count']} "
                    f"sent={data['bytes_sent']}B "
                    f"recv={data['bytes_received']}B "
                    f"conns={data['connection_count']} "
                    f"suspicious={data['suspicious_ports']}"
                )
            except Exception as e:
                print(f"⚠️ 수집 오류: {e}")

            time.sleep(COLLECT_INTERVAL)


if __name__ == "__main__":
    collector = NetworkCollector()
    collector.run()
