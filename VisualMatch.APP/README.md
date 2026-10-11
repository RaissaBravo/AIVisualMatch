# VisualMatch Mobile

Aplicativo Expo/React Native que sincroniza produtos do FastAPI e reconhece produtos offline com o modelo ONNX escolhido no app entre os quatro que a API mantém (MobileNetV2, MobileNetV3-Large, DINOv2-Small ou MobileCLIP2-S0). A rede só é usada na sincronização; fotos e inferências permanecem no aparelho.

## Instalação e Development Build

Requer Node.js **20.19.4 ou superior**, Xcode/CocoaPods ou Android Studio/JDK, e a API em execução, de onde o app baixa o modelo.

```bash
cd VisualMatch.APP
npm install
cp .env.example .env
npx expo prebuild
npx expo run:android # ou: npx expo run:ios
npm run dev
```

Expo Go não serve: Vision Camera e ONNX Runtime possuem módulos nativos. Após instalar o Development Build, `npx expo start --dev-client` atualiza o JavaScript. Refaça build ao mudar módulos/configuração nativa.

## API e cache offline

Defina `EXPO_PUBLIC_API_BASE_URL` sem `/api`: Android Emulator `http://10.0.2.2:8000`; iOS Simulator `http://127.0.0.1:8000`; aparelho físico `http://IP_DO_COMPUTADOR:8000` na mesma rede (Uvicorn com `--host 0.0.0.0`).

O contexto lê Products, ModelInfo e timestamp do AsyncStorage imediatamente e sincroniza em background. A atualização manual busca model-info, valida o contrato, busca os produtos com `?model=<id>` (embeddings só daquele modelo), filtra vetores inválidos, garante o ONNX no aparelho e somente então substitui o cache. Uma falha nunca apaga dados locais.

## Modelo baixado da API

O app não empacota modelo. `src/services/modelStore.ts` baixa `model_url` para `Paths.document/models/<id>-<md5>.onnx`, confere tamanho e MD5 e apaga versões antigas do mesmo modelo. Outros modelos ficam em cache para alternar sem novo download. O modelo é escolhido no topo da tela **Câmera** (`src/components/ModelPicker.tsx`, alimentado por `GET /api/models`). Ao escolher, o app baixa o ONNX (se ainda não estiver em cache) e os embeddings daquele modelo, e só então troca o cache e a sessão da câmera; se falhar, mantém o modelo anterior. A escolha persiste no aparelho, sem novo build. Ao trocar, a sessão ONNX anterior é liberada depois que as inferências em andamento terminam.

Se algum produto não tiver embeddings do modelo escolhido, a sincronização avisa para gerá-los no painel da API.

## Pipeline câmera/ONNX

1. Vision Camera v5 captura uma foto por vez, no máximo a cada 1.000 ms.
2. `calculateCropRegion` desfaz o preview `cover` e converte a ROI central 75% × 45% em pixels da foto orientada.
3. Image Manipulator aplica crop real e resize para a entrada do modelo (`input_width`×`input_height`: 224 ou 256); PNG evita outra perda JPEG.
4. `upng-js` gera pixels RGBA, convertidos para `Uint8Array` RGB NHWC `[1,S,S,3]`.
5. Uma única sessão ONNX processa o tensor. O grafo de cada modelo já faz cast, `/255`, NHWC→NCHW e a normalização própria do modelo.
6. A saída (1280, 384 ou 512 dimensões) recebe L2 normalization e é centralizada pelo centroide das referências. Cada produto usa o maior cosine similarity entre suas referências; o primeiro colocado é match se atingir o limiar e a margem sobre o segundo definidos para o modelo em `MATCH_RULES` (`src/config/recognition.ts`).

Inferências nunca rodam em paralelo nem formam fila. A separação entre inferência e matching permite adicionar smoothing depois.

## Compatibilidade Python/mobile

Adicione `VisualMatch.API/compatibility_test/test_image.jpg` e o modelo, execute `python generate_compatibility_reference.py` no backend e copie os três fixtures para `VisualMatch.APP/compatibility_test`. No Development Build, passe a imagem inteira por `preprocessImage` + `generateEmbedding` e compare com `expected_embedding.json` via `compareEmbeddings`, que retorna diferença máxima, média e cosine similarity. Comece com `rtol=1e-4`, `atol=1e-5`.

O ponto que exige calibração em aparelho é resize bilinear nativo versus Pillow. Neste checkout não existem ONNX, imagem ou embedding esperado, logo a diferença numérica não pôde ser medida.

## Validação

```bash
npm run typecheck
npm run lint
npm test
npx expo-doctor
```

## Estrutura e versões

`app/(tabs)` contém as telas; `src/components`, `context`, `hooks`, `services`, `config`, `types` e `utils` separam UI, sincronização, inferência e matemática. `compatibility_test` recebe os fixtures.

Versões centrais (lockfile): Expo 57.0.18, React Native 0.86.3, Expo Router 57.0.17, Vision Camera 5.2.3, ONNX Runtime RN 1.24.3, AsyncStorage 2.2.0, Image Manipulator 57.0.14, FileSystem 57.0.6 e upng-js 2.1.0.
