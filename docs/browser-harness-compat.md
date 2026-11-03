# browser-harness／Pillow 13：獨立 PyPI 相容套件

## 最新交付狀態

使用者要求正式更新 Hermes release／PyPI 後，相容性 fork 已使用自己的 namespace 發布：

- PyPI：[`browser-harness-hermes-compat==0.1.13.post1`](https://pypi.org/project/browser-harness-hermes-compat/0.1.13.post1/)。**不是 Browser Use 官方 `browser-harness` 發行版。**
- 原始官方來源：`browser-use/browser-harness` v0.1.13，commit `c24e5072ee66f8499bacd663f4f4bcb089bc4492`。
- fork：https://github.com/matttest0080-prog/browser-harness-hermes-compat 。保留 MIT（Copyright 2026 Browser Use）、上游署名與原 README 內容。
- 新發行 source：`c0cb61fb9a78bcac70d48a9ab56a088dc3b4f9cb`，獨立 tag `pypi-v0.1.13.post1`；不是替換原 GitHub-only tag／檔案。
- Publisher／CI：https://github.com/matttest0080-prog/browser-harness-hermes-compat/actions/runs/41414992085 。
- Wheel：`browser_harness_hermes_compat-0.1.13.post1-py3-none-any.whl`，SHA256 `23a52497912d3d5108f51a98d183128e84dd372fa7432a8cb548335d9ab2f161`。
- Sdist：`browser_harness_hermes_compat-0.1.13.post1.tar.gz`，SHA256 `c7f64d13a1d37ab5605469074ea9d7fa9d0360b6e3597d6eb5a80292278d6120`。
- 已匿名從 PyPI 下載 wheel／sdist，分別核對 PyPI JSON digest，並與真正 tag CI 的 3.11 artifacts 逐 byte 相同。不是用較早 PR artifact 的 hash 代替。

Hermes 來源依賴改為上述 registry exact pin，uv.lock／Pi2 locks 固定真正 PyPI hashes。**這個輔助套件已上架，不代表 Hermes 0.22.5.post3 自身已上架**；Hermes 仍須完成 release-ready PR、完整 CI、最新獨立核准、正式 tag 與自己的 publisher。

## 安全修補與身份界線

公開 critical `GHSA-8g5g-8vmr-9782` 影響 Pillow <=12.3.0，首個修補版為 13.0.0。官方 browser-harness 0.1.13 精確要求 Pillow 12.3.0，不能用 uv override、`--no-deps`、偽造 METADATA 或忽略 `pip check` 解決。

本 fork 要求 Pillow 13.0.0，可選 MCP 2.3.0。新 distribution 使用自己的 PyPI 名稱，但保留 `browser_harness` import、`browser-harness`／`browser-harness-mcp` CLI 與 `browser-use` skill identity，Hermes 的 browser_exec 不改成另一套引擎。

新發行僅額外調整身份相關 runtime：版本讀取、PyPI 查詢、更新快取、`uv tool upgrade` 與缺少 MCP 時的安裝提示，均指向獨立 namespace，避免誤更新回官方舊版。瀏覽器操作、daemon／IPC 實作不變。不能只因換了套件名、掃描器沒有這個新 purl 就宣稱修補完成；修補依據仍是 Pillow 13 真實依賴、來源差異、正負控制與消費端驗證。

Hermes 保留全域 **14 日**政策；只有這個已審查 critical 修補相容發行使用具名例外，沒有全域停用新鮮度檢查，也沒有放行無關依賴。此次根鎖版本／來源變更僅為舊 GitHub `browser-harness` → 新 registry namespace，其他套件版本不隨意更新。

## CI、Trusted Publishing 與驗收界線

- Python 3.11–3.14 每組 **266 unit tests passed**，含完整上游測試、JPEG／contact sheet／mask／invalid-image 正負控、namespace 控制、7 個真正 Git objects 的發布 tag 正負控。
- 每組真實 wheel 安裝、`pip check`、import 路徑、`twine check --strict`、同 epoch wheel 重建 byte-identical 通過。
- 每組另建隔離 migration env：先正常安裝官方版，再明確卸除官方 distribution，正常安裝獨立版本並驗 `pip check`、Pillow 13、CLI metadata；沒有 no-deps 或錯誤 suppression。
- namespace 的兩個新負控在舊碼全紅，修正後全綠；更新不會查詢或升級官方 distribution。
- Publisher 僅接受相符的 annotated `pypi-v*` tag，檢查 tag／event／checkout 一致、maintained-branch ancestry、clean worktree；四組 CI 成功後才由 `pypi` environment 的獨立 job 取得短期 OIDC 權限、發布原 CI 產物。無長期 token，PR／build 不持有 publish 權限。
- **不是**真實 Chrome／Browser Use Cloud、模型品質、所有 OS 或長期負載驗收。Hermes registry wheel 與 Pi2 整合另須驗證，不沿用舊 direct-URL artifact 的實裝 receipt。

Hermes 的 PyPI sanitizer 保持 fail-closed：只處理既有明示的 Android psutil／optional source-only backends，不新增任何 browser URL 豁免。新增正向控制確認 registry dependency 保留；原負控仍拒絕未知 core URL 且 wheel bytes 不變。

## 舊版升級：建議全新 venv

官方 `browser-harness` 與獨立套件提供相同 import／CLI 檔案。pip 升級可能留下舊的 orphan distribution 與 Pillow 12 要求，因此**不要直接在舊環境混裝兩者**。也不要先裝新套件、再卸舊套件：卸除同名檔案會破壞新安裝。

Hermes 0.22.5.post3 正式上架後，建議建立新的 `~/.venvs/hermes-iot-0.22.5`，正常安裝 `hermes-agent-iot[minimal]==0.22.5.post3` 並執行 `pip check`／版本與 profile smoke，再由使用者切換服務；保留原 venv／設定／服務供回復。尚未上架前，勿將這段視為可用 PyPI 安裝指令。

若在 disposable env 明確測試遷移，必須先移除舊 `browser-harness`，再正常安裝新依賴並檢查實際 import 與 metadata；不忽略 `pip check`。PM-managed source／bundle 使用 PM 重新建立依賴環境，不用 raw pip／uv 修改既有 Hermes 環境。

## 歷史：GitHub-only 候選

先前為避免相容性衝突，Hermes 使用 `browser-harness` 名稱的固定 GitHub wheel：tag `v0.1.13.post1`、source `f387133ecc9561128d18eabc4af6df143b2560d5`、wheel SHA256 `63a2fb36e398d8a764fb5961a70f0deb63dc60472ff0345b739105d17e2e059e`。四組 CI 各 257 tests 通過，但該 core URL 被原 sanitizer 正確拒絕，所以當時明確暫停 Hermes PyPI 發布。這個舊 tag／artifact 不覆寫，舊實機 receipts 只代表當時候選。

官方日後若發布與安全 Pillow 相容的正式 artifact，應重新審查並移除不必要的 fork，不默默改回仍綁定脆弱 Pillow 的版本。
