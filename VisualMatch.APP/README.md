# VisualMatch Mobile

Aplicativo Expo/React Native que sincroniza produtos do FastAPI e reconhece produtos offline por embeddings MobileNetV2 ONNX. A rede só é usada na sincronização; fotos e inferências permanecem no aparelho.

## Instalação e Development Build

Requer Node.js **20.19.4 ou superior**, Xcode/CocoaPods ou Android Studio/JDK, a API e o mesmo ONNX usado por ela.

```bash
cd VisualMatch.APP
npm install
cp .env.example .env
cp ../VisualMatch.API/models/image-encoder.onnx assets/models/mobilenetv2_embedding.onnx
npx expo prebuild
npx expo run:android # ou: npx expo run:ios
npm run dev
```

Expo Go não serve: Vision Camera e ONNX Runtime possuem módulos nativos. Após instalar o Development Build, `npx expo start --dev-client` atualiza o JavaScript. Refaça build ao mudar módulos/configuração nativa.

## API e cache offline

Defina `EXPO_PUBLIC_API_BASE_URL` sem `/api`: Android Emulator `http://10.0.2.2:8000`; iOS Simulator `http://127.0.0.1:8000`; aparelho físico `http://IP_DO_COMPUTADOR:8000` na mesma rede (Uvicorn com `--host 0.0.0.0`).

O contexto lê Products, ModelInfo e timestamp do AsyncStorage imediatamente e sincroniza em background. A atualização manual busca model-info, valida o contrato, busca produtos, filtra vetores inválidos e somente então substitui o cache. Uma falha nunca apaga dados locais.

## Pipeline câmera/ONNX

1. Vision Camera v5 captura uma foto por vez, no máximo a cada 1.000 ms.
2. `calculateCropRegion` desfaz o preview `cover` e converte a ROI central 75% × 45% em pixels da foto orientada.
3. Image Manipulator aplica crop real e resize 224×224; PNG evita outra perda JPEG.
4. `upng-js` gera pixels RGBA, convertidos para `Uint8Array` RGB NHWC `[1,224,224,3]`.
5. Uma única sessão ONNX processa o tensor. O grafo do backend já faz cast, `/255`, NHWC→NCHW e normalização ImageNet.
6. A saída `[1280]` recebe L2 normalization. Cada produto usa o maior cosine similarity entre suas referências; `>= 0.65` é match e os cinco melhores aparecem ordenados.

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

`app/(tabs)` contém as telas; `src/components`, `context`, `hooks`, `services`, `config`, `types` e `utils` separam UI, sincronização, inferência e matemática. `assets/models` recebe o ONNX e `compatibility_test` os fixtures.

Versões centrais (lockfile): Expo 57.0.18, React Native 0.86.3, Expo Router 57.0.17, Vision Camera 5.2.3, ONNX Runtime RN 1.24.3, AsyncStorage 2.2.0, Image Manipulator 57.0.14, FileSystem 57.0.6 e upng-js 2.1.0.
