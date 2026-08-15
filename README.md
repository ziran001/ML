# 南京虫害预测模型

本工程从南京诱虫记录训练虫害预测模型。每一种害虫单独训练一个模型，训练完成后得到对应的 `.joblib` 文件；这个 `.joblib` 就是后续直接预测时要加载的模型权重。

代码不沿用印度论文中的 `BPH` 字段名，统一使用真实虫种名称和通用字段 `PestCount`。

| 虫种 | 缩写 |
|---|---|
| 稻纵卷叶螟 | RLF |
| 二化螟 | SSB |
| 大螟 | PSB |
| 斜纹夜蛾 | TCW |
| 甜菜夜蛾 | BAW |
| 杨小舟蛾 | PSP |
| 美国白蛾 | FWW |

## 文件结构

```text
code/prepare_nanjing_multi_pest.py   原始 .xls 转周度训练表
code/train_nanjing_multi_pest.py     训练每种害虫的模型权重
code/predict_nanjing_multi_pest.py   加载权重并预测下一周虫量
data/nanjing_multi_pest_weekly.csv   已转换好的周度数据
raw_data/南京诱虫记录/                原始 .xls 上传位置
outputs/                             训练输出目录
```

## 云端重新训练

先把 3 个原始 `.xls` 上传到 `raw_data/南京诱虫记录/`。文件名见 `raw_data/README.md`。

然后运行：

```bash
pip install -r requirements-cloud.txt

python code/prepare_nanjing_multi_pest.py \
  --xls-dir raw_data/南京诱虫记录 \
  --weather-source data/nanjing_weather_weekly_source.csv \
  --output data/nanjing_multi_pest_weekly.csv

python code/train_nanjing_multi_pest.py \
  --input data/nanjing_multi_pest_weekly.csv \
  --out-dir outputs/all_pests
```

只训练三种水稻害虫：

```bash
python code/train_nanjing_multi_pest.py \
  --input data/nanjing_multi_pest_weekly.csv \
  --out-dir outputs/rice_pests \
  --pests RLF SSB PSB
```

训练完成后，`outputs/rice_pests/` 或 `outputs/all_pests/` 中会出现：

```text
model_RLF_*.joblib
model_SSB_*.joblib
model_PSB_*.joblib
model_metrics.csv
trained_model_files.csv
predictions_by_station.csv
feature_names.json
```

其中 `model_*.joblib` 是模型权重，`trained_model_files.csv` 说明每种害虫最终选中了哪个模型文件。

## 使用权重预测

拿训练好的 `.joblib` 模型预测最新一周之后的虫量：

```bash
python code/predict_nanjing_multi_pest.py \
  --input data/nanjing_multi_pest_weekly.csv \
  --model-dir outputs/rice_pests \
  --pests RLF SSB PSB \
  --output outputs/rice_pests/latest_pest_predictions.csv
```

输出：

```text
latest_pest_predictions.csv             每种害虫预测总量
latest_pest_predictions_by_station.csv  每个监测点的预测虫量
```

这里不再输出三类虫之间的相对占比。`Prediction` 就是模型预测的下一周虫量。

## 新数据怎么处理

1. 把新导出的 `.xls` 放进 `raw_data/南京诱虫记录/`。
2. 运行 `prepare_nanjing_multi_pest.py`，重新生成 `data/nanjing_multi_pest_weekly.csv`。
3. 如果只是要用已有权重预测，直接运行 `predict_nanjing_multi_pest.py`。
4. 如果新数据已经积累到一个新季节或新年度，再运行 `train_nanjing_multi_pest.py` 重新训练权重。

GitHub Actions 中的 `Train all Nanjing pest models` 也会执行同样流程，并把训练好的模型权重作为 artifact 提供下载。
