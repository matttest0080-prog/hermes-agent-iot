# Hermes Agent IoT 0.22.5.post3 正式發布紀錄

## 正式來源與產物

- 正式上游固定為 **v0.22.5**，commit `bf0203a794a07aac3ff764972ab9087baa4e4f4e`；不是追上游 main。
- Hermes protected release commit：`250cf28e1fcf3e333959a236010f419647c22f5c`，由 [#53](https://github.com/matttest0080-prog/hermes-agent-iot/pull/53) 正常合併；最新獨立核准對應 head `6a73996e40c7ccd3f3b0dd8ae7723f7d2612a3f0`，合併 tree 相同。
- Annotated tag：[iot-v0.22.5.post3](https://github.com/matttest0080-prog/hermes-agent-iot/releases/tag/iot-v0.22.5.post3)。
- PyPI：[hermes-agent-iot 0.22.5.post3](https://pypi.org/project/hermes-agent-iot/0.22.5.post3/)，上傳時間 `2026-11-03T01:03:34.671597Z`。
- 真正 tag publisher：[41555962510](https://github.com/matttest0080-prog/hermes-agent-iot/actions/runs/41555962510)，build／publish **成功**。`pypi` environment 由獨立 reviewer `matt0080-glitch` 核准，保留 prevent-self-review／OIDC／branch policy。
- 正式檔案只有 wheel，**沒有 Hermes PyPI sdist**：`hermes_agent_iot-0.22.5.post3-py3-none-any.whl`。
- SHA256：`46ae064a902296cb744a16ead141cf4707456b38b8a93d98f510da07b738422a`。
- 匿名 PyPI JSON digest／下載 wheel，與真正 tag CI artifact **逐 byte 相同**；GitHub artifact ZIP digest 亦匹配 API。不是使用 PR／local 候選 hash。
- 正式 METADATA 沒有 direct-URL dependencies，保留 `browser-harness-hermes-compat==0.1.13.post1`；README 影片連結保留，不把影片連結當裝置驗收。

## CI 與失敗紀錄

- [主 CI 41463430829](https://github.com/matttest0080-prog/hermes-agent-iot/actions/runs/41463430829) 在**第 3 次 attempt** 完成必要檢查。前兩次部分 macOS jobs 沒取得 hosted runner（沒有 steps／runner）；第 3 次剩餘 macOS job 真正取得 runner、執行測試並通過。不是把前兩次取消改判成功。
- 真正 tag build 執行 **11 files／104 passed**，包含 build guards、packaging、sanitizer 正負控；正常依賴解析的全新 minimal 安裝、`pip check`、兩個 CLI、installed-prefix／wheel-origin SHA／namespace／resources 檢查通過。
- `iot-v0.22.5.post1` 與 `iot-v0.22.5.post2` 保留原指向，**均未上傳 PyPI**。前者 Linux job 錯要求 Windows-only Git PM artifact；後者 source `PYTHONPATH`／自然生成 egg-info 令 pip 誤判已安裝。修正不使用 force-reinstall／no-deps／偽造 METADATA，也不覆寫 tag。
- PM 正式 relock 只變 Hermes self-version；五份 Pi2 locks 正式再生 byte-identical，保留 ARMv7 hashes／markers／no-build 與無關 pins。14 日政策、具名安全例外及 sanitizer fail-closed 不放寬。

## Pi 2 正式 registry 驗證

實測 Raspberry Pi 2 Model B Rev 1.1／ARMv7／921 MiB RAM／Python 3.13.5；使用全新隔離目錄，整體 **exit 0**，未修改既有服務或環境。

- 正式 registry `hermes-agent-iot==0.22.5.post3` 搭配正式 wheel hash 與原 Pi2 locks 正常解析／安裝，沒有 file-URL 安裝或 no-deps。
- `minimal`／`iot`／`rag`／`full`／`dev` 五份 require-hashes dry-run 均 exit 0；**實際安裝只有 minimal**，不是五個 profiles 都已實裝。
- `pip check` 通過；Hermes／獨立 browser distribution 的 `direct_url.json` 皆不存在，官方 `browser-harness` 未混裝。
- 安裝後 Hermes code／resources／METADATA 與已驗正式 PyPI wheel 逐 byte 相同（排除 pip 正常重寫的 RECORD）；browser 相容套件 bytes 同樣匹配其正式 PyPI wheel。
- **10 smoke**：私密設定與 receipt、重複 setup 不覆寫、context floor 正負控、YAML fallback 清空保留、實際 AIAgent localhost HTTP round trip、無 uvloop／pillow-heif、Pillow 13／JPEG／contact sheet／privacy mask 與 invalid-image 負控。
- **12 SQLite controls**：configure／BEGIN／DDL × expired／non-expired × OperationalError／DatabaseError，含 history／schema 逐 byte 回滾，不放寬原 budget。
- 溫度／throttling 為執行前後取樣，不是長期熱／負載驗收。

## 明確未驗收範圍

- 本次交付限 **PyPI／Pi2**。歷史 Desktop 安裝升級矩陣不是全綠：[41555962970](https://github.com/matttest0080-prog/hermes-agent-iot/actions/runs/41555962970) 的 `v0.19.1` OLD Desktop 安裝仍有 `frimousse` import 無法解析；不改寫舊來源／注入未宣告依賴／把失敗或未執行項判為成功。
- 本次 head 的 optional macOS ARM64 PM bundle 未取得 runner，列為未驗收；不改 labels／保護／測試來繞過。之前 #52 的該 bundle 真正通過，不能替代本次 head。
- localhost HTTP fixture／JPEG 與隱私遮罩／SQLite 正負控，不是真實模型品質、MQTT／Home Assistant、GPIO、Chrome／CDP 或長期負載驗收。

## 升級

建議全新 venv，保留舊環境／設定與服務供回復。官方 `browser-harness` 與相容 distribution 共用 import／CLI，**不可混裝**；見[相容性與遷移](browser-harness-compat.md)。此發布不自動切換既有服務。
