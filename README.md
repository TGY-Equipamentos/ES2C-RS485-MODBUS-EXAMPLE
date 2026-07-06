# Scripts

Utilitários em Python para interagir com dispositivos conectados ao gateway **ES2C-485** via Modbus TCP.

## Requisitos

- Python 3.9 ou superior
- ES2C-485 configurado com **TCP/Modbus** habilitado no webserver
- Acesso de rede ao IP do gateway (porta TCP padrão: **1101**)

## Instalação

Na raiz do repositório ou dentro desta pasta:

```bash
pip install -r requirements.txt
```

## Scripts disponíveis

### `relay_modbus.py`

Controla o módulo de relés **LC Tech 2-way Relay** (Modbus RTU) através do gateway TCP do ES2C-485.

**Manual do módulo:** [LC Tech — documentação](http://www.chinalctech.com/m/view.php?aid=455)

#### Hardware

| Parâmetro        | Valor padrão      |
|------------------|-------------------|
| Endereço Modbus  | 255 (0xFF)        |
| Baud rate        | 9600 8N1          |
| Alimentação      | DC 7–24 V (VCC/GND) |
| RS485            | Jumpers DI→TXD e RO→RXD; linha A+/B− |

> **Atenção:** não alimente o módulo apenas com 5 V — use a faixa indicada pelo fabricante.

#### Uso

```bash
# Ligar relé 1
python relay_modbus.py on --relay 1

# Desligar relé 2
python relay_modbus.py off --relay 2

# Consultar estado dos dois relés
python relay_modbus.py status
```

#### Opções

| Opção         | Padrão           | Descrição                              |
|---------------|------------------|----------------------------------------|
| `--host`      | `192.168.15.130` | IP do ES2C-485                         |
| `--port`      | `1101`           | Porta TCP do gateway Modbus            |
| `--device-id` | `255`            | Endereço Modbus do módulo LC Tech      |
| `--timeout`   | `3.0`            | Timeout da conexão em segundos         |
| `--relay`     | —                | Relé `1` ou `2` (obrigatório em on/off)|

Exemplo com IP customizado:

```bash
python relay_modbus.py on --relay 1 --host 192.168.1.50
```

#### Códigos de saída

| Código | Significado                                      |
|--------|--------------------------------------------------|
| `0`    | Sucesso                                          |
| `1`    | Erro de conexão, rede ou Modbus                  |
| `2`    | Argumentos inválidos (ex.: falta `--relay`)      |

## Solução de problemas

### Não conecta ao gateway

- Confirme o IP e a porta **1101** do ES2C-485.
- Verifique se **TCP/Modbus** está habilitado no webserver do dispositivo.
- Teste conectividade de rede (`ping` ou `telnet` na porta 1101).

### Exceção Modbus `0x0B`

O ES2C enviou o comando RTU, mas não recebeu a resposta de confirmação do módulo. Em comandos de escrita (`on`/`off`), o relé pode ter acionado mesmo assim.

**Sugestão:** reduza o **Frame Gap** no webserver do ES2C para **50–100 ms**.

### Exceção Modbus `0x0A`

Gateway indisponível — frame Modbus inválido ou linha serial ocupada. Verifique cabeamento RS485, endereço do dispositivo e parâmetros seriais.

### Comando enviado sem confirmação

Se o script reportar que o comando foi enviado mas o gateway não confirmou a resposta RS485, observe o LED ou o clique do relé. O script tenta confirmar o estado por leitura após 300 ms; ajustar o Frame Gap costuma resolver.
