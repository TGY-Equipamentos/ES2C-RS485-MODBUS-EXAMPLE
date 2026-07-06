#!/usr/bin/env python3
"""
Aciona módulo LC Tech 2-way Relay Modbus RTU via gateway TCP do ES2C-485.

Manual: http://www.chinalctech.com/m/view.php?aid=455
- Endereço padrão: 255 (0xFF)
- Baud padrão: 9600 8N1
- Alimentação: DC 7-24 V em VCC/GND (não usar só 5 V)
- RS485: jumpers DI→TXD e RO→RXD; comunicação em A+/B-

Requisitos:
  pip install pymodbus

Exemplos:
  python relay_modbus.py on --relay 1
  python relay_modbus.py off --relay 2
  python relay_modbus.py status
"""

from __future__ import annotations

import argparse
import sys
import time

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException
from pymodbus.pdu import ExceptionResponse

DEFAULT_HOST = "192.168.15.130"
DEFAULT_PORT = 1101
DEFAULT_DEVICE_ID = 255
TIMEOUT_S = 3.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Controla relés Modbus via gateway TCP do ES2C-485."
    )
    parser.add_argument(
        "action",
        choices=("on", "off", "status"),
        help="on/off para acionar relé; status para ler os dois canais",
    )
    parser.add_argument(
        "--relay",
        type=int,
        choices=(1, 2),
        help="Relé 1 ou 2 (obrigatório para on/off)",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"IP do ES2C (padrão: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Porta TCP (padrão: {DEFAULT_PORT})")
    parser.add_argument(
        "--device-id",
        type=int,
        default=DEFAULT_DEVICE_ID,
        help=f"Endereço Modbus do módulo LC Tech (padrão: {DEFAULT_DEVICE_ID} = 0xFF)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=TIMEOUT_S,
        help=f"Timeout da conexão em segundos (padrão: {TIMEOUT_S})",
    )
    return parser.parse_args()


def coil_address(relay: int) -> int:
    return relay - 1


def format_modbus_error(response: ExceptionResponse) -> str:
    """Traduz códigos de exceção do gateway ES2C para mensagem legível."""
    code = response.exception_code
    if code == 0x0B:
        return (
            "exceção 0x0B — o ES2C enviou o comando RTU, mas não recebeu a resposta de confirmação. "
            "Em escritas (on/off) o relé pode ter acionado mesmo assim. "
            "Para melhorar: reduza o Frame Gap no webserver (ex.: 50–100 ms)."
        )
    if code == 0x0A:
        return "exceção 0x0A — gateway indisponível (frame Modbus inválido ou serial ocupada)."
    return f"exceção Modbus 0x{code:02X}"


def check_response(response, action: str) -> None:
    if not response.isError():
        return
    if isinstance(response, ExceptionResponse):
        detail = format_modbus_error(response)
        raise ModbusException(f"Falha ao {action}: {detail}")
    raise ModbusException(f"Falha ao {action}: {response}")


def connect_client(host: str, port: int, timeout: float) -> ModbusTcpClient:
    client = ModbusTcpClient(host=host, port=port, timeout=timeout)
    if not client.connect():
        raise ConnectionError(f"Não foi possível conectar em {host}:{port}")
    return client


def read_relay_states(client: ModbusTcpClient, device_id: int, *, strict: bool = True) -> list[bool]:
    response = client.read_coils(address=0, count=2, device_id=device_id)
    if strict:
        check_response(response, "ler coils")
        return list(response.bits[:2])
    if response.isError():
        return []
    return list(response.bits[:2])


def write_relay(client: ModbusTcpClient, relay: int, state: bool, device_id: int) -> bool:
    """Envia comando. Retorna True se o gateway confirmou a resposta RTU."""
    address = coil_address(relay)
    response = client.write_coil(address=address, value=state, device_id=device_id)
    if not response.isError():
        return True
    if isinstance(response, ExceptionResponse) and response.exception_code == 0x0B:
        return False
    check_response(response, f"escrever coil {address}")
    return True


def main() -> int:
    args = parse_args()

    if args.action in ("on", "off") and args.relay is None:
        print("Erro: use --relay 1 ou --relay 2 com on/off.", file=sys.stderr)
        return 2

    client = None
    try:
        client = connect_client(args.host, args.port, args.timeout)

        if args.action == "status":
            states = read_relay_states(client, args.device_id)
            for relay_num, active in enumerate(states, start=1):
                label = "LIGADO" if active else "DESLIGADO"
                print(f"Relé {relay_num}: {label}")
            return 0

        desired = args.action == "on"
        confirmed = write_relay(client, args.relay, desired, args.device_id)
        label = "ligado" if desired else "desligado"

        if confirmed:
            print(
                f"Relé {args.relay} {label} "
                f"(device_id={args.device_id}, coil={coil_address(args.relay)}, confirmado pelo gateway)"
            )
            return 0

        # Gateway não recebeu eco RS485; tenta ler estado para confirmar.
        time.sleep(0.3)
        states = read_relay_states(client, args.device_id, strict=False)
        idx = coil_address(args.relay)
        if len(states) > idx and states[idx] == desired:
            print(
                f"Relé {args.relay} {label} "
                f"(device_id={args.device_id}, coil={idx}, confirmado por leitura de estado)"
            )
            return 0

        print(
            f"Relé {args.relay} {label} — comando enviado; "
            f"gateway não confirmou resposta RS485 (verifique o LED/click do relé). "
            f"Dica: reduza o Frame Gap no ES2C para 50–100 ms."
        )
        return 0

    except ConnectionError as exc:
        print(f"Erro de conexão TCP: {exc}", file=sys.stderr)
        print("Confirme IP, porta 1101 e TCP/Modbus habilitados no webserver.", file=sys.stderr)
        return 1
    except ModbusException as exc:
        print(f"Erro Modbus: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Erro de rede: {exc}", file=sys.stderr)
        return 1
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
