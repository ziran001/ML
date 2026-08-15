# 南京多虫种时序预测

从南京诱虫记录构建“当前周与历史周信息 → 下一自然周虫量”的模型。代码不再使用印度褐飞虱论文的 `BPH` 字段，而使用通用 `PestCount`；虫种保留真实名称和英文缩写。

| 虫种 | 缩写 |
|---|---|
| 稻纵卷叶螟 | RLF |
| 二化螟 | SSB |
| 大螟 | PSB |
| 斜纹夜蛾 | TCW |
| 甜菜夜蛾 | BAW |
| 杨小舟蛾 | PSP |
| 美国白蛾 | FWW |

## 云端运行

```bash
pip install -r requirements-cloud.txt
python code/prepare_nanjing_multi_pest.py \
  --xls-dir "【混沌科技·大田稻麦作物虫害程度自动监测系统】数据收集" \
  --weather-source "虫情预测实验记录/nanjing_weekly_by_station_observed_feature_table.csv" \
  --output data/nanjing_multi_pest_weekly.csv

# 示例：选择三类，输出三个逐周归一化预测权重
python code/train_nanjing_multi_pest.py \
  --input data/nanjing_multi_pest_weekly.csv \
  --out-dir outputs/three_pests \
  --pests RLF SSB PSB

# 不传 --pests 时训练全部可用虫种
python code/train_nanjing_multi_pest.py \
  --input data/nanjing_multi_pest_weekly.csv \
  --out-dir outputs/all_pests
```

## 两个核心脚本做什么

`prepare_nanjing_multi_pest.py` 是原始数据转换器。它读取监测系统导出的 `.xls`，识别真实虫种，按网关和日期去重，把日诱虫量汇总为周诱虫量，再与南京周气象表合并，输出统一的 `PestCount` 长表。以后有新数据时，把新 `.xls` 放入原始数据目录并重新运行该脚本即可；它会递归扫描目录。

`train_nanjing_multi_pest.py` 是训练器。它按虫种构造严格连续周的滞后和滚动特征，用较早年份训练、2024 年留出测试，比较多个模型，并为每个虫种保存 RMSE 最低的 `.joblib` 模型。这里的 `.joblib` 文件就是可直接加载使用的训练权重。

## 使用训练好的权重预测最新数据

仓库同时提供 `predict_nanjing_multi_pest.py`。它加载每个虫种的最佳 `.joblib` 文件，对输入表中每个监测点的最新一周预测下一周虫量，并输出所选虫种的归一化权重。

```bash
python code/predict_nanjing_multi_pest.py \
  --input data/nanjing_multi_pest_weekly.csv \
  --model-dir outputs/three_pests \
  --pests RLF SSB PSB \
  --output outputs/latest_three_pest_weights.csv
```

输出包括总体权重文件和带 `_by_station` 后缀的逐监测点预测文件。三个权重表示三类虫预测总量的相对占比，不是模型内部特征重要性。

## 新数据更新流程

1. 将平台新导出的 `.xls` 放入 `raw_data/`，保留原来的表头结构。
2. 更新南京天气周表；若暂时没有新天气，缺失字段会由模型中位数填补，但预测质量可能下降。
3. 重新运行转换脚本，生成更新后的周表。
4. 只需日常预测时，直接运行预测脚本并复用现有权重。
5. 数据积累到新的完整季节或新年度后，再运行训练脚本更新权重。

每类虫分别比较 RandomForest、ExtraTrees、GradientBoosting、Stacking；安装可选依赖后还会自动加入 XGBoost、LightGBM 和 CatBoost。测试严格使用 2024 年，训练使用更早数据。

主要输出：`model_metrics.csv`、`predictions_by_station.csv`、`pest_prediction_weights.csv` 和每虫种最佳模型文件。权重定义为同一预测周内各虫种预测总量占所选虫种预测总量之比，因此选择三类时每周恰好输出三个权重且总和为 1。

