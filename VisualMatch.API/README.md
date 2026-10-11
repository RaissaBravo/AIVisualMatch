# VisualMatch API

Backend FastAPI para cadastro de produtos e extração de características visuais com quatro modelos ONNX (MobileNetV2, MobileNetV3-Large, DINOv2-Small, MobileCLIP2-S0). Cada foto guarda um embedding L2-normalizado por modelo, persistido como JSON de floats no SQLite (`image_embeddings`), e a API mantém todos atualizados. O app escolhe o modelo e baixa da própria API o ONNX e os embeddings dele, então os dois lados sempre usam o mesmo arquivo e o mesmo pipeline.

## Arquitetura

- `app/main.py`: inicialização, banco, sessão ONNX única e arquivos estáticos.
- `app/routers/`: API REST e administração HTML server-side.
- `app/config.py`: registro de modelos (`MODELS`); o primeiro é o padrão de requisições sem `?model=`.
- `app/services/embedding_service.py`: inspeção do ONNX, pré-processamento, inferência e `ModelRegistry` com uma sessão por modelo.
- `app/services/image_service.py`: validação real com Pillow, armazenamento UUID e cleanup.
- `data/products.db`: SQLite criado automaticamente.
- `images/{product_id}/`: arquivos físicos; nomes originais nunca formam o path.
- `models/<id>.onnx`: um arquivo por modelo registrado; só `mobilenetv2.onnx` é versionado, os demais são gerados por `scripts/export_models.py`.

Excluir um produto remove os registros em cascata e sua pasta. Uploads têm limite de 15 MB e aceitam conteúdo JPEG, PNG ou WEBP validado por decodificação, não apenas pela extensão/MIME. Se um lote falhar, seus arquivos e registros são revertidos.

## Instalação e execução

Requer Python 3.11 ou superior.

```bash
cd VisualMatch.API
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Admin: http://localhost:8000/
- Swagger: http://localhost:8000/docs
- API: http://localhost:8000/api

Para acessar a API a partir de um celular na mesma rede Wi-Fi, use o IP local do Mac no app (por exemplo, `EXPO_PUBLIC_API_BASE_URL=http://192.168.1.194:8000`). O endereço `0.0.0.0` serve apenas para o Uvicorn escutar em todas as interfaces; ele não deve ser usado como URL no celular.

Um modelo sem ONNX fica indisponível (`available: false` em `/api/models`, com o comando para gerá-lo) e é ignorado; os demais seguem funcionando, e os embeddings dele são gerados no próximo start depois que o arquivo existir. Sem nenhum ONNX, upload e regeneração retornam `503`. Isso evita inferência simulada em produção.

Na inicialização, bancos criados antes do suporte a vários modelos são migrados automaticamente: a coluna `product_images.embedding` vira linhas `mobilenetv2` em `image_embeddings`. Backups antigos também são aceitos e migrados ao restaurar.

## Modelos ONNX

Todos os modelos seguem o mesmo contrato: recebem `uint8` NHWC `[N,S,S,3]` no input `input`, incorporam no próprio grafo o cast para float, divisão por 255, transposição para NCHW e a normalização do modelo, e retornam features float32 no output `embedding`. Na carga, nomes, shapes, dtype, layout e dimensão são validados contra o registro em `app/config.py`, e a API calcula tamanho e MD5 do arquivo para o app verificar o download.

| id | Origem | S | Saída | Normalização no grafo |
| --- | --- | --- | --- | --- |
| `mobilenetv2` | torchvision `IMAGENET1K_V2`, `features` + global average pooling | 224 | 1280 | ImageNet mean/std |
| `mobilenetv3` | torchvision MobileNetV3-Large `IMAGENET1K_V2`, `features` + global average pooling (antes do classificador) | 224 | 960 | ImageNet mean/std |
| `dinov2-small` | timm `vit_small_patch14_dinov2.lvd142m`, token CLS | 224 | 384 | ImageNet mean/std |
| `mobileclip2-s0` | open_clip `MobileCLIP2-S0` (`dfndr2b`), torre visual reparametrizada com projeção CLIP | 256 | 512 | apenas `/255` |

Os pesos do MobileCLIP2 usam a Apple Machine Learning Research Model License, que só permite pesquisa não comercial. Use-o para experimentar; não o distribua em produto comercial.

Só `mobilenetv2.onnx` é versionado. Para gerar os demais (uma vez por máquina; `run-macos.sh` e `run-windows.bat` fazem isso sozinhos), use um ambiente separado para não pesar o da API:

```bash
python -m venv .venv-export
.venv-export/bin/pip install -r requirements-export.txt
.venv-export/bin/python scripts/export_models.py                  # todos os que faltam
.venv-export/bin/python scripts/export_models.py dinov2-small     # reexporta um modelo
```

O script baixa os pesos das fontes oficiais, exporta opset 17 em um único arquivo e confere a saída do ONNX contra o PyTorch. Com as versões fixadas em `requirements-export.txt`, a exportação é reproduzível byte a byte (mesmo MD5 em toda máquina). Ao substituir o arquivo de um modelo, regenere os embeddings dele; o app detecta o novo MD5 e baixa a nova versão na próxima sincronização.

Cada embedding guarda o MD5 do ONNX que o gerou (`image_embeddings.model_md5`). Na inicialização, a API gera, em todos os modelos carregados, os embeddings que faltam ou que vieram de outra versão do arquivo, antes de aceitar requisições, e registra o resultado no log. Uma imagem ilegível é registrada como erro, sem impedir o start. Linhas anteriores ao versionamento (sem MD5) são consideradas atuais. Embeddings desatualizados nunca são enviados ao app.

Novas imagens recebem embeddings de todos os modelos carregados. Sem reiniciar a API, use **Gerar pendentes** na tabela de modelos do painel (gera só os que faltam ou estão desatualizados) ou `POST /api/regenerate-all-embeddings?model=<id>` (regera todos).

### Comparando modelos

```bash
python scripts/evaluate_models.py [--threshold 0.45] [--margin 0.08]
```

Usa cada foto do catálogo como consulta contra as demais, com a mesma regra do app (subtração do centroide, melhor referência por produto, limiar e margem), e informa acerto top-1, margem mediana e taxas de match certo/errado. O banco é aberto somente para leitura. Fotos de catálogo não são frames de câmera: use o resultado para ordenar os modelos e calibre os limiares no aparelho.

## Pipeline exato e contrato mobile

A resposta real de `GET /api/model-info?model=<id>` é o contrato canônico e reflete os metadados inspecionados daquele modelo. O algoritmo em `EmbeddingService.preprocess_image` é (S = tamanho de entrada do modelo):

1. abrir e decodificar com Pillow;
2. aplicar orientação EXIF (`exif_transpose`);
3. converter para RGB;
4. distorcer/enquadrar a imagem inteira diretamente em S×S (sem crop e sem letterbox);
5. resize bilinear do Pillow;
6. manter os pixels como `uint8` HWC e adicionar o batch, produzindo `[1,S,S,3]`;
7. dentro do próprio ONNX: cast para float32 e divisão por `255.0`;
8. dentro do ONNX: transposição NHWC→NCHW;
9. dentro do ONNX: por canal RGB, calcular `(x - mean) / std` com os valores do modelo (informados em `normalization`);
10. executar o tensor de entrada uint8 contíguo;
11. executar o output único de features detectado;
12. achatar a saída para vetor float32;
13. calcular `v / ||v||₂`, rejeitando norma zero e valores NaN/Infinity.

No mobile, atenção especial às diferenças de implementação de orientação EXIF e resize bilinear. Não use `centerCrop`, normalização `[-1,1]`, BGR nem logits. O endpoint informa os nomes/shapes efetivamente encontrados e nunca inventa dimensão quando ela é dinâmica e ainda não houve inferência.

Embeddings normalizados permitem similaridade de cosseno por produto escalar: `similarity = dot(query_embedding, stored_embedding)`. Compare a consulta contra todas as fotos de cada produto e defina a estratégia de agregação/limiar no aplicativo.

## API

- `GET /api/model-info[?model=<id>]` — contrato de um modelo (padrão: `mobilenetv2`), com `model_url`, `model_size` e `model_md5`
- `GET /api/models` — todos os modelos, com contrato, disponibilidade e cobertura (`embedded_images`, `outdated_images`, `missing_images`); o app monta o seletor de modelo com ela
- `GET /api/models/{id}/file` — download do ONNX usado pelo app
- `GET /api/products[?model=<id>]` — embeddings de um único modelo (padrão: o ativo)
- `GET /api/products/{id}`
- `POST /api/products` — multipart: `name`, zero ou mais `images`
- `PUT /api/products/{id}` — multipart: `name`, zero ou mais `images`
- `POST /api/products/{id}/images` — multipart com um ou mais `images`
- `DELETE /api/products/{id}/images/{image_id}`
- `DELETE /api/products/{id}`
- `POST /api/products/{id}/regenerate-embeddings`
- `POST /api/regenerate-all-embeddings[?model=<id>]` — sem `model`, regenera todos os modelos carregados

Na tela administrativa, **Baixar banco de dados** gera `visualmatch-backup.zip` com
`data/products.db` e a árvore `images/`. **Sobrescrever banco de dados** aceita um
ZIP nesse mesmo formato, valida integralmente o SQLite e as imagens e só então
substitui o catálogo atual.

`GET /api/products` retorna somente `id`, `name` e uma lista de embeddings por foto, sem paths internos, nunca misturando modelos. O detalhe também fornece metadados, URL pública e os embeddings atuais de cada imagem por modelo (`embeddings: {id: vetor}`).

## Compatibilidade Python/mobile

1. Fixe o ONNX que será distribuído.
2. Coloque uma foto representativa em `compatibility_test/test_image.jpg`.
3. Execute `python generate_compatibility_reference.py [id-do-modelo]` (padrão: `mobilenetv2`).
4. Versione a imagem, `expected_embedding.json` e `model_info.json` junto da versão do modelo (o `.gitignore` atual evita inclusão acidental; remova as regras quando decidir versioná-los).
5. No app, execute a mesma imagem e contrato de pré-processamento.
6. Compare inicialmente com `np.allclose(mobile, python, rtol=1e-4, atol=1e-5)` e também inspecione similaridade de cosseno. Só aumente tolerâncias após diagnosticar a etapa divergente.

## Testes

```bash
pytest -q
```

Os testes de CRUD/upload usam um extrator determinístico injetado, portanto não falsificam o estado do serviço em execução. O teste de inferência real roda para cada modelo registrado, verifica repetibilidade, dimensão, contrato de entrada, float32, finitude e norma unitária, e é ignorado para modelos cujo ONNX ainda não foi exportado.
