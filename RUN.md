# VisualMatch

VisualMatch é um sistema de reconhecimento visual de produtos composto por uma API em FastAPI e um aplicativo mobile em React Native com Expo. Produtos e suas imagens são cadastrados pelo painel web da API; o backend mantém embeddings de quatro modelos ONNX (MobileNetV2, MobileNetV3-Large, DINOv2-Small e MobileCLIP2-S0) e o aplicativo escolhe um deles e sincroniza seus embeddings para reconhecer produtos diretamente pela câmera.

Depois da sincronização, a captura, a inferência e a comparação acontecem localmente no aparelho. As fotos capturadas pela câmera não são enviadas para a API, e os produtos já sincronizados continuam disponíveis sem conexão.

| Python Backend (API / Admin) | React-Native App |
| -------- | -------- |
| <img width="600" height="470" alt="image" src="https://github.com/user-attachments/assets/e57921b1-e1c0-45aa-b11f-1ccc22ac01db" /> | <img width="320" height="694" alt="image" src="https://github.com/user-attachments/assets/a8fa5076-211f-41b7-b4ac-d6043d95d1ed" /> |

## Componentes

- `VisualMatch.API`: FastAPI, painel administrativo, SQLite, armazenamento de imagens e geração de embeddings com ONNX Runtime.
- `VisualMatch.APP`: Expo/React Native, câmera nativa, ONNX Runtime no aparelho, cache offline e comparação por similaridade de cosseno.
- `VisualMatch.API/models/<id>.onnx`: um arquivo por modelo registrado em `VisualMatch.API/app/config.py`.

> A API é a fonte única dos modelos. Ao escolher um modelo, o app baixa da API o ONNX dele (verificado por MD5) e os embeddings desse mesmo modelo; não há cópia manual de arquivos. Veja [Modelos de embedding](#modelos-de-embedding).

## Pré-requisitos

Para todos os ambientes:

- Git;
- Python 3.11 ou superior;
- Node.js 20.19.4 ou superior;
- um celular e o computador conectados à mesma rede local, para testar em aparelho físico.

Para desenvolvimento mobile:

- macOS: Xcode e CocoaPods para iOS; Android Studio e JDK para Android;
- Windows: Android Studio e JDK para Android;
- um Development Build do Expo, pois Expo Go não inclui Vision Camera e ONNX Runtime.

O build nativo para iOS requer macOS e Xcode. No Windows, desenvolva e execute a versão Android localmente; para gerar iOS, use um Mac ou um serviço de build remoto compatível com Expo.

## Instalação no macOS

Clone o repositório e entre na pasta:

```bash
git clone https://github.com/RaissaBravo/AIVisualMatch.git
cd AIVisualMatch
```

### 1. API

```bash
cd VisualMatch.API
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Com a API em execução:

- painel administrativo: `http://localhost:8000/`;
- Swagger: `http://localhost:8000/docs`;
- endpoints REST: `http://localhost:8000/api`.

### 2. Aplicativo

Em outro terminal, a partir da raiz do repositório:

```bash
cd VisualMatch.APP
npm install
cp .env.example .env.local
```

Edite `VisualMatch.APP/.env.local` e informe o IP local do Mac:

```env
EXPO_PUBLIC_API_BASE_URL=http://192.168.1.100:8000
```

Substitua `192.168.1.100` pelo IP real do computador. No macOS, ele pode ser consultado em **Ajustes do Sistema → Rede** ou, para Wi-Fi, com:

```bash
ipconfig getifaddr en0
```

Gere e instale o Development Build:

```bash
npx expo prebuild
npx expo run:ios --device
```

Para Android no macOS, use:

```bash
npx expo run:android
```

Depois que o Development Build estiver instalado, inicie o Metro:

```bash
npm run dev
```

### Atalho para desenvolvimento no macOS

Depois de concluir a instalação da API, do app e do `socat`, você pode iniciar API, proxy e Metro com um único comando executado na raiz do repositório:

```bash
./run-macos.sh
```

O script descobre o IP atual do Mac, inicia a API apenas em `127.0.0.1:8000`, publica a porta `8001` na rede local com `socat` e atualiza `EXPO_PUBLIC_API_BASE_URL=http://IP_DO_MAC:8001` no `.env.local`. O Metro é iniciado com o cache limpo para incorporar o novo endereço. Pressione `Ctrl+C` para encerrar os três processos.

Na primeira utilização, caso o arquivo ainda não esteja executável, rode:

```bash
chmod +x run-macos.sh
```

## Instalação no Windows

No PowerShell:

```powershell
git clone https://github.com/RaissaBravo/AIVisualMatch.git
cd AIVisualMatch
```

### 1. API

```powershell
cd VisualMatch.API
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Se a política do PowerShell bloquear a ativação do ambiente virtual, libere scripts para o usuário atual e tente novamente:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 2. Aplicativo Android

Em outro PowerShell, a partir da raiz:

```powershell
cd VisualMatch.APP
npm install
Copy-Item .env.example .env.local
```

Descubra o IPv4 do computador com `ipconfig` e edite `.env.local`:

```env
EXPO_PUBLIC_API_BASE_URL=http://192.168.1.100:8000
```

Em seguida:

```powershell
npx expo prebuild
npx expo run:android
npm run dev
```

No Android Emulator, em vez do IP da máquina, também é possível usar `http://10.0.2.2:8000`. Em celular físico, use o IPv4 do computador na rede local.

### Atalho para desenvolvimento no Windows

Depois de instalar a API e o app, inicie API e Metro com um único comando na raiz do repositório (ou com duplo clique no arquivo):

```powershell
.\run-windows.bat
```

O `.bat` chama `run-windows.ps1` com a ExecutionPolicy liberada só para essa execução e faz o mesmo que o `run-macos.sh`:

- confere Node.js 20.19.4+, `VisualMatch.API\.venv` e `node_modules`;
- exporta os ONNX que ainda não existirem;
- descobre o IPv4 da interface com rota padrão e grava `EXPO_PUBLIC_API_BASE_URL=http://IP:8000` no `.env.local`;
- inicia a API com `--reload` e o Metro com cache limpo.

`Ctrl+C` encerra os dois. As portas podem ser trocadas com `VISUALMATCH_API_PORT` e `VISUALMATCH_METRO_PORT`.

Diferente do macOS, não há proxy: a API escuta direto em `0.0.0.0:8000`. Na primeira execução, permita o Python quando o Windows perguntar, ou crie a regra de firewall indicada pelo script (PowerShell como administrador, veja [Comunicação entre o celular e a API](#comunicação-entre-o-celular-e-a-api)).

## Comunicação entre o celular e a API

`localhost` ou `127.0.0.1` dentro de um celular físico aponta para o próprio celular, não para o computador. Por isso, o app deve usar o IP local da máquina em `VisualMatch.APP/.env.local`:

```env
EXPO_PUBLIC_API_BASE_URL=http://IP_DO_COMPUTADOR:8000
```

Não acrescente `/api` ao valor. Depois de alterar `.env.local`, reinicie o Metro; se necessário, limpe o cache:

```bash
npx expo start --dev-client --clear
```

Teste primeiro pelo navegador do celular:

```text
http://IP_DO_COMPUTADOR:8000/api/model-info
```

Se a página não abrir, confira:

1. celular e computador estão na mesma rede Wi-Fi e a rede não possui isolamento de clientes;
2. a API foi iniciada com `--host 0.0.0.0`;
3. o IP em `.env.local` é o IP atual do computador;
4. VPNs não estão bloqueando ou desviando o tráfego local;
5. o firewall permite conexões TCP de entrada na porta 8000.

No Windows, permita a porta em um PowerShell executado como administrador:

```powershell
New-NetFirewallRule -DisplayName "VisualMatch API" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000
```

No macOS, autorize conexões de entrada para Python quando o sistema solicitar ou ajuste em **Ajustes do Sistema → Rede → Firewall**. Faça essas liberações apenas em uma rede confiável.

### Alternativas com proxy local

Normalmente os proxies abaixo não são necessários. Eles são úteis quando a API responde em `127.0.0.1:8000`, mas a exposição direta para a rede continua bloqueada.

No Windows:

```powershell
npx iisexpress-proxy 8000 to 8001
```

No macOS, instale o `socat` e encaminhe a porta 8001 para a API local:

```bash
brew install socat
socat TCP-LISTEN:8001,fork,reuseaddr,bind=0.0.0.0 TCP:127.0.0.1:8000
```

Ao usar qualquer uma dessas alternativas, libere a porta TCP 8001 no firewall e altere o app para usar a porta do proxy:

```env
EXPO_PUBLIC_API_BASE_URL=http://IP_DO_COMPUTADOR:8001
```

## Primeiro uso

1. Inicie a API e abra `http://localhost:8000/` no computador.
2. Cadastre produtos e envie imagens representativas pelo painel administrativo.
3. Inicie o aplicativo e abra a tela **Produtos**.
4. Toque em atualizar para sincronizar produtos, embeddings e o arquivo do modelo.
5. Abra a tela **Câmera** e posicione um produto dentro da área indicada.

Se o modelo não estiver presente, a API ainda inicia e permite produtos sem fotos, mas informa `available: false` em `/api/model-info`; uploads que precisam gerar embeddings ficam indisponíveis até o ONNX ser instalado.

## Modelos de embedding

| id | Modelo | Entrada | Dimensão | ONNX | Licença dos pesos |
| --- | --- | --- | --- | --- | --- |
| `mobilenetv2` | MobileNetV2 (ImageNet) | 224×224 | 1280 | 8,9 MB, versionado | BSD-3-Clause |
| `mobilenetv3` | MobileNetV3-Large (ImageNet) | 224×224 | 960 | 12 MB, gerado localmente | BSD-3-Clause |
| `dinov2-small` | DINOv2 ViT-S/14 | 224×224 | 384 | 83 MB, gerado localmente | Apache-2.0 |
| `mobileclip2-s0` | MobileCLIP2-S0 | 256×256 | 512 | 44 MB, gerado localmente | Apple AMLR: **somente pesquisa, uso comercial proibido** |

Todos os modelos recebem o mesmo tensor `uint8` RGB NHWC e fazem a normalização dentro do grafo, então só o tamanho da entrada muda entre eles.

**A API mantém todos prontos.** Cada imagem guarda um embedding por modelo. Ao iniciar, a API gera os que faltam ou ficaram desatualizados em todos os modelos antes de começar a responder, e cada upload novo já recebe os quatro. O painel administrativo mostra se os 4 modelos estão prontos, a cobertura de cada um e, por imagem, o status em cada modelo.

**O app escolhe qual usar.** Na tela **Câmera**, toque no nome do modelo no topo e escolha outro. O app baixa da API o ONNX desse modelo (só na primeira vez; depois fica em cache no aparelho) e os embeddings dele, e a câmera passa a usá-lo. Volte à câmera e teste de novo para comparar. A escolha fica salva no aparelho, e a tela **Info** mostra o modelo em uso, o arquivo baixado e a regra de match.

### Em outra máquina

Só o `mobilenetv2.onnx` (8,5 MB) fica no git. O MobileNetV3 (12 MB), o DINOv2 (83 MB) e o MobileCLIP2 (44 MB) ficam fora porque o repositório é público, os arquivos passam do limite recomendado pelo GitHub e a licença do MobileCLIP2 só permite uso em pesquisa, com regras próprias de redistribuição. Cada máquina gera os seus a partir dos pesos oficiais (torchvision e Hugging Face Hub):

- **`run-macos.sh` ou `run-windows.bat`:** nada a fazer. Se algum ONNX não existir, o script cria `VisualMatch.API/.venv-export` com PyTorch (na primeira vez leva alguns minutos e ~2 GB) e exporta os que faltam antes de subir a API.
- **Manual (Windows ou sem o script):**

  ```bash
  cd VisualMatch.API
  python -m venv .venv-export
  .venv-export/bin/pip install -r requirements-export.txt     # Windows: .venv-export\Scripts\pip
  .venv-export/bin/python scripts/export_models.py            # exporta todos os que faltam
  ```

`requirements-export.txt` fixa as versões de PyTorch, timm, open_clip e onnx. Com elas a exportação gera arquivos **idênticos byte a byte** (mesmo MD5), então os embeddings de um backup feito em outra máquina continuam válidos. Se o arquivo sair diferente, a API percebe pelo MD5 e regera os embeddings daquele modelo na inicialização, e o app baixa a nova versão na próxima sincronização.

O catálogo (`data/products.db` e `images/`) também não está no git: leve-o com **Baixar banco de dados** / **Sobrescrever banco de dados** no painel. Ao restaurar, a API gera os embeddings pendentes de todos os modelos.

Os limiares de reconhecimento ficam por modelo em `VisualMatch.APP/src/config/recognition.ts` (`MATCH_RULES`) e precisam ser calibrados no aparelho. Para comparar os modelos no seu catálogo antes de ir para a câmera, rode `python scripts/evaluate_models.py` na API: ele faz uma avaliação leave-one-out com a mesma regra de match do app, sem alterar o banco.

## Testes e validação

Backend:

```bash
cd VisualMatch.API
source .venv/bin/activate  # macOS
pytest -q
```

No Windows, use `.\.venv\Scripts\Activate.ps1` para ativar o ambiente.

Aplicativo:

```bash
cd VisualMatch.APP
npm run typecheck
npm run lint
npm test
npx expo-doctor
```

## Mais informações

Consulte a documentação específica de cada componente:

- [`VisualMatch.API/README.md`](VisualMatch.API/README.md)
- [`VisualMatch.APP/README.md`](VisualMatch.APP/README.md)

## Segurança e uso em produção

Os comandos deste README são voltados ao desenvolvimento em rede local. Antes de publicar o sistema, configure autenticação, HTTPS, política de CORS conforme os clientes permitidos, armazenamento persistente, backup do banco e um servidor de produção no lugar do `uvicorn --reload`.
