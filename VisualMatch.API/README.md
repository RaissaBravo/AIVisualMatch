# VisualMatch API

Backend FastAPI para cadastro de produtos e extração de características visuais com MobileNetV2 ONNX. Cada foto possui seu próprio embedding L2-normalizado, persistido como JSON de floats no SQLite. O mesmo arquivo ONNX e o mesmo pipeline devem ser usados no aplicativo React Native/Expo.

## Arquitetura

- `app/main.py`: inicialização, banco, sessão ONNX única e arquivos estáticos.
- `app/routers/`: API REST e administração HTML server-side.
- `app/services/embedding_service.py`: inspeção do ONNX, pré-processamento e inferência.
- `app/services/image_service.py`: validação real com Pillow, armazenamento UUID e cleanup.
- `data/products.db`: SQLite criado automaticamente.
- `images/{product_id}/`: arquivos físicos; nomes originais nunca formam o path.
- `models/image-encoder.onnx`: fonte única de verdade do modelo.

Excluir um produto remove os registros em cascata e sua pasta. Uploads têm limite de 15 MB e aceitam conteúdo JPEG, PNG ou WEBP validado por decodificação, não apenas pela extensão/MIME. Se um lote falhar, seus arquivos e registros são revertidos.

## Instalação e execução

Requer Python 3.11 ou superior.

```bash
cd VisualMatch.API
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

- Admin: http://localhost:8000/
- Swagger: http://localhost:8000/docs
- API: http://localhost:8000/api

Sem o ONNX, o servidor inicia e produtos sem fotos podem ser mantidos. Upload e regeneração retornam `503` com o caminho esperado do modelo; `/api/model-info` retorna `available: false`. Isso evita inferência simulada em produção.

## Modelo ONNX

O modelo atual fica em `models/image-encoder.onnx`. Ele foi inspecionado: recebe `uint8` NHWC `[1,224,224,3]` no input `input`, incorpora no próprio grafo o cast para float, divisão por 255, transposição para NCHW e normalização ImageNet, e retorna features float32 `[1,1280]` no output `embedding`. Na carga, nomes, shapes, dtype, layout e dimensão são novamente validados.

Para gerar a versão de referência deste repositório:

```bash
pip install -r requirements-export.txt
python scripts/export_mobilenetv2_to_onnx.py
```

O script baixa `torchvision.models.MobileNet_V2_Weights.IMAGENET1K_V2`, incorpora o mesmo pré-processamento uint8 NHWC ao grafo, remove o classificador, mantém `features`, aplica global average pooling e exporta opset 17. Substituir o arquivo exige regenerar todos os embeddings e redistribuir exatamente o mesmo ONNX ao mobile.

## Pipeline exato e contrato mobile

A resposta real de `GET /api/model-info` é o contrato canônico e reflete os metadados inspecionados. O algoritmo em `EmbeddingService.preprocess_image` é:

1. abrir e decodificar com Pillow;
2. aplicar orientação EXIF (`exif_transpose`);
3. converter para RGB;
4. distorcer/enquadrar a imagem inteira diretamente em 224×224 (sem crop e sem letterbox);
5. resize bilinear do Pillow;
6. manter os pixels como `uint8` HWC e adicionar o batch, produzindo `[1,224,224,3]`;
7. dentro do próprio ONNX: cast para float32 e divisão por `255.0`;
8. dentro do ONNX: transposição NHWC→NCHW;
9. dentro do ONNX: por canal RGB, calcular `(x - mean) / std`, com mean `[0.485, 0.456, 0.406]` e std `[0.229, 0.224, 0.225]`;
10. executar o tensor de entrada uint8 contíguo;
11. executar o output único de features detectado;
12. achatar a saída para vetor float32;
13. calcular `v / ||v||₂`, rejeitando norma zero e valores NaN/Infinity.

No mobile, atenção especial às diferenças de implementação de orientação EXIF e resize bilinear. Não use `centerCrop`, normalização `[-1,1]`, BGR nem logits. O endpoint informa os nomes/shapes efetivamente encontrados e nunca inventa dimensão quando ela é dinâmica e ainda não houve inferência.

Embeddings normalizados permitem similaridade de cosseno por produto escalar: `similarity = dot(query_embedding, stored_embedding)`. Compare a consulta contra todas as fotos de cada produto e defina a estratégia de agregação/limiar no aplicativo.

## API

- `GET /api/model-info`
- `GET /api/products`
- `GET /api/products/{id}`
- `POST /api/products` — multipart: `name`, zero ou mais `images`
- `PUT /api/products/{id}` — multipart: `name`, zero ou mais `images`
- `POST /api/products/{id}/images` — multipart com um ou mais `images`
- `DELETE /api/products/{id}/images/{image_id}`
- `DELETE /api/products/{id}`
- `POST /api/products/{id}/regenerate-embeddings`
- `POST /api/regenerate-all-embeddings`

`GET /api/products` retorna somente `id`, `name` e uma lista de embeddings por foto, sem paths internos. O detalhe também fornece metadados e URL pública de cada imagem.

## Compatibilidade Python/mobile

1. Fixe o ONNX que será distribuído.
2. Coloque uma foto representativa em `compatibility_test/test_image.jpg`.
3. Execute `python generate_compatibility_reference.py`.
4. Versione a imagem, `expected_embedding.json` e `model_info.json` junto da versão do modelo (o `.gitignore` atual evita inclusão acidental; remova as regras quando decidir versioná-los).
5. No app, execute a mesma imagem e contrato de pré-processamento.
6. Compare inicialmente com `np.allclose(mobile, python, rtol=1e-4, atol=1e-5)` e também inspecione similaridade de cosseno. Só aumente tolerâncias após diagnosticar a etapa divergente.

## Testes

```bash
pytest -q
```

Os testes de CRUD/upload usam um extrator determinístico injetado, portanto não falsificam o estado do serviço em execução. O teste de inferência real verifica repetibilidade, dimensão, float32, finitude e norma unitária, e é marcado como ignorado enquanto o ONNX não existir.
