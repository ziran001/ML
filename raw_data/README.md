# 原始数据放置说明

本目录用于放南京原始数据，云端重新训练时需要先把本地原始表上传到这里。

## 需要上传的原始文件

把以下 3 个诱虫记录表上传到：

`raw_data/南京诱虫记录/`

| 文件 | 大小 | 用途 |
|---|---:|---|
| `江苏省南京市六合区、江苏省南京市江宁区等雄州钱仓二化螟二化螟、大螟等2023-01-01至2024-12-31诱虫记录.xls` | 3,429,376 bytes | 二化螟、大螟及其它共表诱虫记录 |
| `江苏省南京市江宁区、江苏省南京市江宁区等淳化街道稻纵稻纵卷叶螟2023-06-01至2023-10-30诱虫记录.xls` | 440,832 bytes | 2023 稻纵卷叶螟诱虫记录 |
| `江苏省南京市江宁区、江苏省南京市江宁区等淳化街道稻纵稻纵卷叶螟2024-06-01至2024-10-30诱虫记录.xls` | 444,416 bytes | 2024 稻纵卷叶螟诱虫记录 |

天气/观测源表已作为 CSV 放在仓库：

`data/nanjing_weather_weekly_source.csv`

如果你后续有更新版天气表，也可以上传到：

`raw_data/南京天气/nanjing_weekly_by_station_observed_feature_table.csv`

然后运行转换脚本时把 `--weather-source` 指向这个新文件。

## 网页上传方式

1. 打开 `https://github.com/ziran001/ML/tree/main/raw_data`。
2. 进入或新建 `南京诱虫记录` 文件夹。
3. 点击 `Add file` -> `Upload files`。
4. 拖入上面 3 个 `.xls` 文件并提交。

## 命令上传方式

如果本机或云端已安装并登录 GitHub CLI：

```bash
gh repo clone ziran001/ML
cd ML
mkdir -p raw_data/南京诱虫记录
# 将 3 个 .xls 文件复制到 raw_data/南京诱虫记录/
git add raw_data/南京诱虫记录/*.xls
git commit -m "Add raw Nanjing trap workbooks"
git push
```

## 云端从原始数据重训

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

只训练三类虫：

```bash
python code/train_nanjing_multi_pest.py \
  --input data/nanjing_multi_pest_weekly.csv \
  --out-dir outputs/three_pests \
  --pests RLF SSB PSB
```
