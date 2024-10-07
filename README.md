# forensicface

<!-- WARNING: THIS FILE WAS AUTOGENERATED! DO NOT EDIT! -->

## Install

``` sh
pip install forensicface
```

Os arquivos onnx dos modelos de detecção (det_10g.onnx), pose
(1k3d68.onnx) e gênero/idade (genderage.onnx) devem estar na pasta
`~/.insightface/models/<model_name>/`

O arquivo onnx do modelo de reconhecimento (adaface_ir101web12m.onnx)
deve estar na pasta `~/.insightface/models/<model_name>/adaface/`

O arquivo onnx do modelo de qualidade CR_FIQA (cr_fiqa_l.onnx) deve
estar na pasta `~/.insightface/models/<model_name>/cr_fiqa/`

O modelo padrão é denominado `sepaelv2`. Se você utilizar `sepaelv2` como <model_name> não será preciso passar o nome do modelo durante a inicialização.

## Como utilizar

Importação da classe ForensicFace:

``` python
from forensicface.app import ForensicFace
```

Instanciamento do ForensicFace:

``` python
ff = ForensicFace(det_size=320, use_gpu=True, extended=True)
```

    Applied providers: ['CUDAExecutionProvider', 'CPUExecutionProvider'], with options: {'CPUExecutionProvider': {}, 'CUDAExecutionProvider': {'device_id': '0', 'gpu_mem_limit': '18446744073709551615', 'gpu_external_alloc': '0', 'gpu_external_free': '0', 'gpu_external_empty_cache': '0', 'cudnn_conv_algo_search': 'EXHAUSTIVE', 'cudnn_conv1d_pad_to_nc1d': '0', 'arena_extend_strategy': 'kNextPowerOfTwo', 'do_copy_in_default_stream': '1', 'enable_cuda_graph': '0', 'cudnn_conv_use_max_workspace': '1', 'tunable_op_enable': '0', 'enable_skip_layer_norm_strict_mode': '0', 'tunable_op_tuning_enable': '0'}}
    find model: /home/rafael/.insightface/models/sepaelv2/1k3d68.onnx landmark_3d_68 ['None', 3, 192, 192] 0.0 1.0
    Applied providers: ['CUDAExecutionProvider', 'CPUExecutionProvider'], with options: {'CPUExecutionProvider': {}, 'CUDAExecutionProvider': {'device_id': '0', 'gpu_mem_limit': '18446744073709551615', 'gpu_external_alloc': '0', 'gpu_external_free': '0', 'gpu_external_empty_cache': '0', 'cudnn_conv_algo_search': 'EXHAUSTIVE', 'cudnn_conv1d_pad_to_nc1d': '0', 'arena_extend_strategy': 'kNextPowerOfTwo', 'do_copy_in_default_stream': '1', 'enable_cuda_graph': '0', 'cudnn_conv_use_max_workspace': '1', 'tunable_op_enable': '0', 'enable_skip_layer_norm_strict_mode': '0', 'tunable_op_tuning_enable': '0'}}
    find model: /home/rafael/.insightface/models/sepaelv2/det_10g.onnx detection [1, 3, '?', '?'] 127.5 128.0
    Applied providers: ['CUDAExecutionProvider', 'CPUExecutionProvider'], with options: {'CPUExecutionProvider': {}, 'CUDAExecutionProvider': {'device_id': '0', 'gpu_mem_limit': '18446744073709551615', 'gpu_external_alloc': '0', 'gpu_external_free': '0', 'gpu_external_empty_cache': '0', 'cudnn_conv_algo_search': 'EXHAUSTIVE', 'cudnn_conv1d_pad_to_nc1d': '0', 'arena_extend_strategy': 'kNextPowerOfTwo', 'do_copy_in_default_stream': '1', 'enable_cuda_graph': '0', 'cudnn_conv_use_max_workspace': '1', 'tunable_op_enable': '0', 'enable_skip_layer_norm_strict_mode': '0', 'tunable_op_tuning_enable': '0'}}
    find model: /home/rafael/.insightface/models/sepaelv2/genderage.onnx genderage ['None', 3, 96, 96] 0.0 1.0
    set det-size: (320, 320)

## Processamento básico de imagens

Obter pontos de referência, distância interpupilar, representação
vetorial, a face alinhada com dimensão fixa (112x112), estimativas de
sexo, idade, pose (*pitch*, *yaw*, *roll*) e qualidade.

``` python
results = ff.process_image_single_face("obama.png")
results.keys()
```

    /home/rafael/miniconda3/envs/ffdev/lib/python3.10/site-packages/insightface/utils/transform.py:68: FutureWarning: `rcond` parameter will change to the default of machine precision times ``max(M, N)`` where M and N are the input matrix dimensions.
    To use the future default and silence this warning we advise to pass `rcond=None`, to keep using the old, explicitly pass `rcond=-1`.
      P = np.linalg.lstsq(X_homo, Y)[0].T # Affine matrix. 3 x 4

    dict_keys(['keypoints', 'ipd', 'embedding', 'norm', 'bbox', 'aligned_face', 'gender', 'age', 'pitch', 'yaw', 'roll', 'fiqa_score'])

Comparar duas imagens faciais e obter o escore de similaridade.

``` python
ff.compare("obama.png", "obama2.png")
```

    0.8556093

Agregar embeddings de duas imagens faciais em uma única representação,
com ponderação por qualidade

``` python
agg = ff.aggregate_from_images(["obama.png", "obama2.png"], quality_weight=True)
agg.shape
```

    (512,)

## Estimativa de qualidade CR-FIQA

Estimativa de qualidade pelo método
[CR-FIQA](https://github.com/fdbtrs/CR-FIQA)

Para desabilitar, instancie o forensicface com a opção extended = False:

`ff = ForensicFace(extended=False)`

Obs.: a opção `extended = False` também desabilita as estimativas de
sexo, idade e pose.

``` python
good = ff.process_image("001_frontal.jpg")
bad = ff.process_image("001_cam1_1.jpg")
good["fiqa_score"], bad["fiqa_score"]
```

    (2.3786173, 1.4386057)

## Crédito dos modelos utilizados

- Detecção, gênero (M/F), idade e pose (pitch, yaw, roll):
  [insightface](https://github.com/deepinsight/insightface)

- Reconhecimento: [adaface](https://github.com/mk-minchul/AdaFace)

- Estimativa de qualidade: [CR-FIQA](https://github.com/fdbtrs/CR-FIQA)
