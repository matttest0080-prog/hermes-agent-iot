<div dir="rtl">

<p align="center">
  <img src="assets/banner.png" alt="Hermes Agent IoT" width="100%">
</p>

# ہرمیس ایجنٹ IoT (Hermes Agent IoT)

> Raspberry Pi 2 / ARMv7، MQTT، Home Assistant، روبوٹکس اور کم وسائل والے edge AI کے لیے ہلکا پھلکا Hermes Agent۔

<p align="center">
  <a href="https://pypi.org/project/hermes-agent-iot/"><img src="https://img.shields.io/badge/PyPI-hermes--agent--iot-blue?style=for-the-badge" alt="PyPI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <a href="https://github.com/NousResearch/hermes-agent"><img src="https://img.shields.io/badge/Upstream-NousResearch%2Fhermes--agent-blueviolet?style=for-the-badge" alt="Upstream Hermes Agent"></a>
  <a href="README_PI2.md"><img src="https://img.shields.io/badge/Raspberry%20Pi%202-ARMv7-C51A4A?style=for-the-badge&logo=raspberrypi&logoColor=white" alt="Raspberry Pi 2"></a>
</p>

<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/Lang-English-lightgrey?style=for-the-badge" alt="English"></a>
  <a href="README.es.md"><img src="https://img.shields.io/badge/Lang-Español-orange?style=for-the-badge" alt="Español"></a>
  <a href="README.ur-pk.md"><img src="https://img.shields.io/badge/Lang-اردو-green?style=for-the-badge" alt="اردو"></a>
  <a href="README.zh-CN.md"><img src="https://img.shields.io/badge/Lang-中文-red?style=for-the-badge" alt="中文"></a>
</p>

ہرمیس ایجنٹ IoT [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) کا ایک IoT/روبوٹکس پر مرکوز فورک ہے۔ مینٹین شدہ `pi2-lite` برانچ محدود Raspberry Pi اور edge تعیناتیوں پر توجہ مرکوز کرتی ہے جبکہ upstream Hermes Agent کے رن ٹائم اور ایکو سسٹم کو محفوظ رکھتی ہے۔

## ہرمیس ایجنٹ IoT کیوں؟

- **Raspberry Pi 2 / ARMv7:** 1 GB کلاس ہارڈویئر کے لیے تصدیق شدہ کم وسائل والا انسٹالیشن طریقہ۔
- **IoT پروفائلز:** MQTT، Home Assistant، MCP/ACP اور remote-first RAG کے لیے ڈیپینڈنسی پروفائلز۔
- **Edge-first تعیناتی:** بھاری AI انفرینس کو ریموٹ رکھیں جبکہ Raspberry Pi ایجنٹ آرکیسٹریشن اور ڈیوائس انٹیگریشن سنبھالے۔
- **روبوٹکس کی سمت:** GPIO، I2C، PWM، سینسرز، ایکچویٹرز اور روبوٹکس سکلز کی بنیاد۔
- **Upstream سے آگاہ:** IoT اور ARMv7 کمپیٹیبلٹی تبدیلیوں کا جائزہ تیز رفتار upstream ڈیولپمنٹ سے الگ رکھا جاتا ہے۔

## فوری آغاز — Raspberry Pi 2

ہرمیس ایجنٹ IoT کو Python `>=3.11,<3.14` کی ضرورت ہے۔ اسے ورچوئل انوائرمنٹ میں انسٹال کریں:

<div dir="ltr">

```bash
python3 --version
python3 -m venv ~/.venvs/hermes-iot
source ~/.venvs/hermes-iot/bin/activate
python -m pip install --upgrade pip
python -m pip install 'hermes-agent-iot[minimal]==0.20.5.post2'
python -m pip check

hermes-iot setup --profile minimal
hermes-iot profile show
hermes setup model
hermes
```

</div>

> سسٹم pip، `sudo pip` یا `--break-system-packages` استعمال نہ کریں۔

### سورس چیک آؤٹ

جب آپ کو ریپوزٹری کے مکمل وسائل درکار ہوں تو مینٹین شدہ `pi2-lite` برانچ استعمال کریں:

<div dir="ltr">

```bash
git clone --branch pi2-lite --depth 1 \
  https://github.com/matttest0080-prog/hermes-agent-iot.git
cd hermes-agent-iot
bash setup-pi2-minimal.sh --profile minimal
source ~/.hermes-venv/bin/activate
hermes setup model
hermes
```

</div>

> کلون ڈائریکٹری کو محفوظ رکھیں۔ سورس انسٹالر قابل تدوین (editable) Python انسٹالیشن استعمال کرتا ہے، اس لیے چیک آؤٹ کو منتقل یا حذف کرنے سے انوائرمنٹ خراب ہو سکتا ہے۔

## انسٹالیشن پروفائلز

<div dir="ltr">

| پروفائل | مطلوبہ ہدف |
| --- | --- |
| `minimal` | Raspberry Pi 2 / ARMv7 / 1 GB بیس لائن |
| `iot` | MQTT، Home Assistant، MCP/ACP اور متعلقہ IoT انٹیگریشنز |
| `rag` | IoT کے علاوہ Honcho / remote-first RAG |
| `full` | زیادہ طاقتور Raspberry Pi، ARM64، x86 edge سرور یا VM |
| `dev` | کنٹریبیوٹر اور ڈیولپمنٹ سسٹمز |

</div>

PyPI extra اور setup پروفائل کو یکساں رکھیں۔ مثال کے طور پر:

<div dir="ltr">

```bash
python -m pip install 'hermes-agent-iot[iot]==0.20.5.post2'
hermes-iot setup --profile iot
```

</div>

`full` اور `dev` Raspberry Pi 2 / 1 GB سسٹمز کے لیے تجویز نہیں کیے جاتے۔

## پروجیکٹ کی حیثیت

<div dir="ltr">

| صلاحیت | حیثیت |
| --- | --- |
| Raspberry Pi 2 / ARMv7 minimal انسٹالیشن | ✅ تصدیق شدہ |
| عوامی PyPI پیکج | ✅ دستیاب |
| کم سے کم ڈیپینڈنسی پروفائل | ✅ دستیاب |
| IoT ڈیپینڈنسی پروفائل | ✅ دستیاب |
| MQTT انٹیگریشن | ✅ دستیاب |
| Home Assistant انٹیگریشن | ✅ دستیاب |
| Remote-first RAG | ✅ دستیاب |
| روبوٹکس دستاویزات | ✅ دستیاب |
| GPIO ایبسٹریکشن | 🛠 روڈ میپ |
| I2C ڈیوائس لیئر | 🛠 روڈ میپ |
| PWM / سروو کنٹرول | 🛠 روڈ میپ |
| سینسر پلگ ان فریم ورک | 🛠 روڈ میپ |
| ESP32 MQTT برج | 🛠 روڈ میپ |

</div>

## دستاویزات

- [IoT پروجیکٹ کا جائزہ](IOT_PROJECT.md) — پروجیکٹ کے اہداف، سپورٹ کی حیثیت، پروفائلز اور روڈ میپ۔
- [Raspberry Pi 2 فوری آغاز](README_PI2.md) — ڈیپینڈنسی میٹرکس، کنفیگریشن پروفائلز اور Pi2 حفاظتی رہنمائی۔
- [Raspberry Pi 2 مینوئل](RASPBERRY_PI2_MANUAL.md) — Pi2 تعیناتی کی تفصیلی دستاویزات۔
- [روبوٹکس](ROBOTICS.md) — روبوٹکس انٹیگریشن نوٹس۔
- [سیکیورٹی پالیسی](SECURITY.md) — کمزوری کی اطلاع اور حفاظتی رہنمائی۔
- [Upstream Hermes Agent دستاویزات](https://hermes-agent.nousresearch.com/docs/) — عمومی Hermes Agent فیچرز، پرووائیڈرز، گیٹ ویز، ڈیسک ٹاپ/سرور استعمال اور انٹیگریشنز۔

## Upstream بمقابلہ Hermes Agent IoT

<div dir="ltr">

| شعبہ | Upstream Hermes Agent | Hermes Agent IoT |
| --- | --- | --- |
| عمومی ڈیسک ٹاپ/سرور ایجنٹ | بنیادی ہدف | upstream بنیاد استعمال کرتا ہے |
| Raspberry Pi 2 / ARMv7 | بنیادی ہدف نہیں | بنیادی کمپیٹیبلٹی ہدف |
| 1 GB کلاس minimal پروفائل | عمومی ڈیپینڈنسی ماڈل | مخصوص `minimal` پروفائل |
| MQTT / Home Assistant تعیناتی | عمومی انٹیگریشنز | مخصوص `iot` پروفائل |
| کم وسائل والی edge تعیناتی | عمومی رن ٹائم | فورک کا بنیادی فوکس |
| روبوٹکس | عمومی ایجنٹ دائرہ | IoT/روبوٹکس پر مبنی دستاویزات اور روڈ میپ |

</div>

یہ فورک جان بوجھ کر upstream `main` سے پیچھے رہ سکتا ہے جب تک ڈیپینڈنسی تبدیلیوں، IoT پیچز اور ARMv7 کمپیٹیبلٹی کا جائزہ لے کر تصدیق نہیں ہو جاتی۔ عمومی ڈیسک ٹاپ/سرور استعمال کے لیے upstream پروجیکٹ کو ترجیح دیں۔

## تصدیق شدہ ریلیز

موجودہ تصدیق شدہ بیس لائن:

- PyPI: [`hermes-agent-iot 0.20.5.post2`](https://pypi.org/project/hermes-agent-iot/0.20.5.post2/)
- Tag: `iot-v0.20.5.post2`
- Python: `>=3.11,<3.14`
- فزیکل تصدیق: Raspberry Pi 2 Model B Rev 1.1، 32-bit ARMv7، 921 MiB RAM، Python 3.13.5

`minimal` وہیل بیس لائن کو فزیکل Raspberry Pi 2 ہارڈویئر پر کلین انسٹال اور smoke test کیا گیا۔ بھاری اختیاری extras کو اپنے ڈیپینڈنسی سیٹ کے مطابق ہارڈویئر درکار ہوتا ہے۔

## Pi2 سورس انسٹالیشن کو اپ ڈیٹ کرنا

اپ ڈیٹس کو ہمیشہ `pi2-lite` برانچ پر مقید رکھیں:

<div dir="ltr">

```bash
cd ~/hermes-agent-iot
source ~/.hermes-venv/bin/activate

git status --short
git switch pi2-lite
git fetch origin pi2-lite
git merge --ff-only origin/pi2-lite

bash setup-pi2-minimal.sh --profile minimal
```

</div>

`minimal` کو اصل میں انسٹال کردہ پروفائل سے بدلیں۔ IoT release 0.20.4 اور بعد میں، بغیر آرگیومنٹ والا `hermes update` `hermes-agent-iot` ڈسٹری بیوشن کو پہچان کر `pi2-lite` کو ڈیفالٹ کرتا ہے؛ آٹومیشن میں آڈٹ ایبلٹی کے لیے واضح `--branch pi2-lite` اب بھی مفید ہے۔ سورس اپ ڈیٹ کے بعد پروفائل انسٹالر دوبارہ چلائیں۔

## روڈ میپ

<div dir="ltr">

- [x] Raspberry Pi 2 / ARMv7 انسٹالیشن طریقہ
- [x] کم وسائل والا ڈیپینڈنسی پروفائل
- [x] IoT ڈیپینڈنسی پروفائل
- [x] MQTT / Home Assistant انٹیگریشن طریقہ
- [x] عوامی PyPI پیکج
- [x] فزیکل Raspberry Pi 2 تصدیق
- [ ] GPIO ایبسٹریکشن
- [ ] I2C ڈیوائس ایبسٹریکشن
- [ ] PWM / سروو کنٹرول
- [ ] سینسر پلگ ان فریم ورک
- [ ] روبوٹکس سکل فریم ورک
- [ ] ESP32 MQTT برج
- [ ] Raspberry Pi 3 / 4 / 5 تصدیقی میٹرکس

</div>

## Upstream ڈیسک ٹاپ / سرور انسٹالیشن

ہرمیس ایجنٹ IoT بنیادی طور پر Raspberry Pi اور edge تعیناتیوں کے لیے ہے۔ عمومی ڈیسک ٹاپ یا سرور استعمال کے لیے upstream Hermes Agent انسٹال کریں۔

### Windows (مقامی PowerShell)

<div dir="ltr">

```powershell
iex (irm https://hermes-agent.nousresearch.com/install.ps1)
```

</div>

### Linux / macOS / WSL2

<div dir="ltr">

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

</div>

یہ upstream انسٹالرز اس فورک کے Pi2 مخصوص پروفائلز یا IoT پیکیجنگ کو انسٹال نہیں کرتے۔

## Hermes Agent کے بارے میں

ہرمیس ایجنٹ [Nous Research](https://nousresearch.com) کا تیار کردہ خود کو بہتر بنانے والا AI ایجنٹ ہے۔ یہ ٹرمینل انٹرفیس، مستقل سیکھنے اور میموری، شیڈول شدہ آٹومیشنز، سب ایجنٹس، متعدد ایگزیکیوشن بیک اینڈز، میسجنگ گیٹ ویز اور متعدد LLM پرووائیڈرز کی سپورٹ فراہم کرتا ہے۔

ہرمیس ایجنٹ IoT upstream پروجیکٹ کی جگہ نہیں لیتا۔ یہ اس بنیاد کو Raspberry Pi 2، ARMv7، کم وسائل والے edge نوڈز، MQTT/Home Assistant ماحول اور مستقبل کی روبوٹکس انٹیگریشنز کے لیے ڈھالتا ہے۔

## لائسنس اور انتساب

ہرمیس ایجنٹ IoT [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) سے ماخوذ ہے اور اس ریپوزٹری کے [MIT لائسنس](LICENSE) کی پیروی کرتا ہے۔ ماخوذ کام کو دوبارہ تقسیم کرتے وقت upstream کاپی رائٹ اور انتساب محفوظ رکھیں۔

</div>
