# 官方模板

两处原文，句子不要混用：

- 本机 Comfy 官方模板：https://docs.comfy.org/zh/tutorials/image/qwen/qwen-image-2-1
- 模型卡：https://github.com/QwenLM/Qwen-Image-2.1

## 文生图

自然英文句子。顺序是主体、环境、画法、构图。

模型卡示例：`A man in a well-tailored navy suit walks out of a Manhattan office building, adjusting his tie under the bright midday sun.`

## 透明底

角色和道具用这一节。描述放在两句中间。

本机 Comfy 官方句，这台机器已经用它画出带透明通道的 PNG：

```text
This is an RGBA format image with transparency. {描述}. The image has an alpha channel and a transparent background.
```

模型卡原句，不要和上面混用：

```text
This is an RGBA image with transparency. {描述}. The image has alpha channel and the background is transparent.
```

透明像素的颜色通道是紫色。看图软件不认透明通道时会显示成紫底，这不是没抠干净。保存 PNG。

示例：

```text
This is an RGBA format image with transparency. A single small black tadpole in side view, round head, two dot eyes, one thin tail, Chinese ink wash on empty space, centered. The image has an alpha channel and a transparent background.
```

中文意思：一条侧面的小黑蝌蚪，圆脑袋，两点眼睛，一根细尾巴，水墨，居中，透明底。

## 场景

不要套透明底。横图，画面里不要角色。

示例：`A wide Chinese ink-wash lotus pond, a few pale gray lotus leaves, one pale pink lotus flower, distant leaves even lighter, empty rice paper, no animals.`

中文意思：横构图的水墨荷塘，几片淡墨荷叶，一枝淡粉荷花，远处更淡，没有动物。

## 改图

模型卡原句：

```text
Edit the image using the prompt: {改什么}.
```

## 多图

模型卡原句：

```text
Picture 1 is {图1是什么}. Picture 2 is {图2是什么}. Edit according to {怎么改} based on Picture 1 and Picture 2.
```

接口里引用各张图时写成 `<image1>`、`<image2>`。

## 分辨率

边长用 16 的倍数。角色和道具用 1024×1024。场景用 1024×576。官方预设还有 2048×2048、2688×1536、1536×2688。

## 本机参数

已在 `192.168.0.200:8188` 测过：

- 模型：`qwen_image_2.1_int8_convrot.safetensors`
- 文本编码器：`qwen3vl_8b_int8_convrot.safetensors`，类型 `qwen_image`
- VAE：`qwen_image_2.1_vae_bf16.safetensors`
- `euler` + `simple`，cfg 1，25 步

cfg 为 1 时负面词无效，留空。官方管线默认 40 到 50 步。25 步已经能用，不要为了更像先加步数。
