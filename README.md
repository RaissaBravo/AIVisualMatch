# VisualMatch

VisualMatch é um sistema de reconhecimento visual de produtos composto por uma API em FastAPI e um aplicativo mobile em React Native com Expo. Produtos e suas imagens são cadastrados pelo painel web da API; o backend gera embeddings com MobileNetV2/ONNX e o aplicativo os sincroniza para reconhecer produtos diretamente pela câmera.

Depois da sincronização, a captura, a inferência e a comparação acontecem localmente no aparelho. As fotos capturadas pela câmera não são enviadas para a API, e os produtos já sincronizados continuam disponíveis sem conexão.

## Componentes

- `VisualMatch.API`: FastAPI, painel administrativo, SQLite, armazenamento de imagens e geração de embeddings com ONNX Runtime.
- `VisualMatch.APP`: Expo/React Native, câmera nativa, ONNX Runtime no aparelho, cache offline e comparação por similaridade de cosseno.
- `VisualMatch.API/models/image-encoder.onnx`: modelo usado para gerar os embeddings no backend.
- `VisualMatch.APP/assets/models/mobilenetv2_embedding.onnx`: cópia do mesmo modelo usada pelo aplicativo.

> O backend e o aplicativo precisam usar exatamente o mesmo arquivo ONNX. Ao trocar o modelo, copie a nova versão para o app e regenere os embeddings dos produtos.

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
cp ../VisualMatch.API/models/image-encoder.onnx assets/models/mobilenetv2_embedding.onnx
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
Copy-Item ..\VisualMatch.API\models\image-encoder.onnx assets\models\mobilenetv2_embedding.onnx
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

1. Confirme que os dois diretórios contêm o mesmo modelo ONNX.
2. Inicie a API e abra `http://localhost:8000/` no computador.
3. Cadastre produtos e envie imagens representativas pelo painel administrativo.
4. Inicie o aplicativo e abra a tela **Produtos**.
5. Toque em atualizar para sincronizar os produtos e embeddings.
6. Abra a tela **Câmera** e posicione um produto dentro da área indicada.

Se o modelo não estiver presente, a API ainda inicia e permite produtos sem fotos, mas informa `available: false` em `/api/model-info`; uploads que precisam gerar embeddings ficam indisponíveis até o ONNX ser instalado.

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
