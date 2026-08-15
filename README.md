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

每类虫分别比较 RandomForest、ExtraTrees、GradientBoosting、Stacking；安装可选依赖后还会自动加入 XGBoost、LightGBM 和 CatBoost。测试严格使用 2024 年，训练使用更早数据。

主要输出：`model_metrics.csv`、`predictions_by_station.csv`、`pest_prediction_weights.csv` 和每虫种最佳模型文件。权重定义为同一预测周内各虫种预测总量占所选虫种预测总量之比，因此选择三类时每周恰好输出三个权重且总和为 1。

