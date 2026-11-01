# v0.22.5 同步審查（尚未完成驗收）

建立：2026-10-30；補記：2026-11-01。工作分支：`sync/upstream-v0.22.5`。

> 本文件是合併候選的驗證紀錄，不是遠端已合併或可發布聲明。本機 merge commit 用於驗證依賴 Git HEAD 的 fixture；遠端仍須完整 CI 與獨立 reviewer，禁止繞過分支保護。

## 固定來源

- fork 原始 HEAD：`ded7f91de28b56ebe861874c3026346e3e6fe719`。
- 上游正式版：`v0.22.5`，annotated tag object `56b6a31fededdf7364e1a0a79548d144e7fd81a3`，實際 commit `bf0203a794a0`（完整值以 `git rev-parse v0.22.5^{commit}` 為準）。
- 目標套件版本：`0.22.5.post1`。未追蹤上游 main，未建立發布 tag 或上傳 PyPI。

## 已修正的合併回歸

先在乾淨上游 worktree 重跑：自訂端點標頭、safe-worker、native HTTP 認證、次要 profile 外掛 host、delegation routing，5 個測試檔共 73 項通過，確認原合併樹的失敗不是上游既有行為。

重新整合 `agent/agent_init.py`、`agent/auxiliary_client.py`、`agent/agent_runtime_helpers.py`、`hermes_cli/web_server.py`，恢復上游的新認證、safe-worker、credential pool 分域、memory provider 初始化、fallback 路由、快取與 logging 邏輯。保留 fork 的低 context floor、模型切換 rollback、強制原生 asyncio。context floor 驗證拆至 `agent/agent_init_context_floor.py`，沒有用新增 health 豁免掩蓋檔案成長。

另外修正：

- 模型切換以 builder 最終採用的 `api_mode` 建立 runtime snapshot；MoA 測試不再以吞例外假通過。
- fork 的 Weixin／Yuanbao ingress 回歸測試改用上游搬遷後的 plugin import。
- 恢復 E2E workflow 的 tmux 前置檢查與 messaging-gated 測試步驟。
- Windows marker 測試保留標準 runner 的時限，但恢復 process-handle 等待，不以固定 sleep 或可重用 PID 判斷結束。
- Desktop 的 simple-git v4 實作及測試恢復上游版本，保留具名 import；補回 argv-parser 及 WebSocket dependency。

## 依賴與鎖檔

- 保留 fork 的 14 日新鮮度政策及逐套件安全修補例外，未全域關閉 age gate。
- 同步 `mcp==2.3.0`、`aiohttp==3.14.5`、`PyJWT==2.15.1`、`certifi==2026.10.19`；補回上游 Python 3.14 的 ruamel C parser 平台宣告。
- 新 Pi 2 generator 分別解析 Python 3.11–3.13 的五種 profile，加入 PiWheels ARMv7 雜湊，排除 uvloop／pillow-heif。直接 pin 更新時，僅其相依閉包跟隨已審查的根鎖檔，避免舊 `mcp-types`／`yarl` constraint 阻擋安全更新；其餘舊 constraint 保留。新增 5 項 generator 行為測試，含版本分域、雜湊冪等與排除套件負控。
- 根 workspace `npm ci` 成功，後續 npm audit 為 0 項；Desktop typecheck 與 simple-git 16 項測試通過。
- website 安全 pins 與鎖檔也已更新：npm audit 為 **5 項 low，0 moderate/high/critical**，不是全專案零漏洞。原始 JSON 在本機證據目錄。

### 尚未解決：Pillow 與 browser-harness

上游以 uv override 將 Pillow 提至 13.0.0；`browser-harness==0.1.13` 發布 metadata 仍精確要求 `pillow==12.3.0`。fork 目前仍維持 12.3.0，不能宣稱已涵蓋上游 Pillow 13 的安全修補。Pi 2 已確認能下載 Pillow 13 的 cp313／ARMv7 wheel，所以不是「ARMv7 沒有 wheel」。但直接提高 pin 會破壞一般 pip 的依賴解析與 `pip check`；必須先設計並驗證合法的相容處理，不能以 `--no-deps`、偽造 metadata 或忽略檢查當作正式解法。

## 已實測範圍

### 桌面端

- 修正後第一批：7 個測試檔，101 項通過。
- MoA／rollback：2 個測試檔，14 項通過。
- workflow 回歸：2 個測試檔，7 項通過。
- 更新依賴後：7 個測試檔，110 項通過（generator、packaging、Pi 2 guard、YAML C parser、MCP OAuth、plugin ingress）。
- `scripts/check --base MERGE_HEAD`：12 項檢查曾通過，health 0 blocking／0 advisory。後續 YAML writer 及文件修改仍須在最終索引快照再驗證。
- YAML writer 新增 3 項 regression tests，先證明修正前全紅；修正後含既有註解／縮排測試，共 27 項通過。
- `uv lock --check`、`git diff --check HEAD` 通過。

### Pi 2 實機

設備：`armv7l`、Python 3.13.5。使用獨立 `~/hermes-v0225-validation/venv`，不是取代既有服務環境。

- 更新後的 minimal／iot／rag／full／dev 五組鎖檔，全數通過 `pip install --dry-run --ignore-installed --require-hashes`；dev 另補跑取得明確 exit 0。
- minimal 先行實際安裝，後升級至更新鎖檔的 IoT dependencies 與本機建置 wheel；`pip check` 通過。
- 最新 wheel 的 7 項 smoke 關卡通過：私有設定／env／receipt 權限、版本與 profile、重複 setup 不覆寫負控、低於 context floor 拒絕負控、附註解 fallback list 清空仍為有效 YAML、真實 `AIAgent` 至 localhost HTTP fixture 的一輪請求／回覆、無 uvloop／pillow-heif。
- **這不是**實際模型品質、MQTT 實體設備、Home Assistant 連線、長期負載或壽命驗證。Python 3.11／3.12 不得寫成 Pi 實機驗證。

## 完整測試與合併阻擋

首輪完整 Python suite 已完成：6,624 個檔案、66,818 passed、52 failed、1,026 skipped，另有 1 個 pytest 非零退出的檔案。首輪 JS workspace 6/10 checks 通過、4 項失敗。這些大跑混合了修正前後時間點及舊 interpreter／Git，不能視為最終 commit 的驗收。

目前正以正確 PATH、Python 3.14、具 archive filter 的 Python 3.11.15、較新 Git、tmux 及獨立虛擬顯示器重跑。進度與結果以系統暫存目錄下 `hermes-v0225-evidence/` 的日誌及 `.exit` 為準；未取得最終結果前，不能宣稱完整 CI 通過。

Desktop UI 初輪 11,509 passed、3 failed：已確認 storage instance spy 在 jsdom 下無法攔截 Storage prototype、timer 數量受其他 store 的合法 timer 影響。改為正確 spy 與可觀察的 debounce 行為後，兩檔 32 項通過。NVIDIA 主機的 entry bundle 測試改測明確 Wayland hint，避免錯誤假設主機沒有 NVIDIA；含 ticket bridge 及既有平台策略測試，4 檔 16 項通過。全 UI 與 Electron lane 另行重跑，不能用定向測試代替。

原先 31 個失敗測試檔在乾淨上游重跑，結果 343 passed、16 failed、3 skipped。包含測試工具／venv 位置相關問題，以及上游 checkout 同樣失敗的 recovery、Telegram admission、installer 測試。已另確認 plugin validator 會從 PATH 呼叫 bootstrap `python3`；本機未啟用 venv 時選到系統 Python 3.10，使用正確 PATH 後該定向測試通過。這是失敗歸因證據，不是豁免它們的理由。部分本機 suite 先前的失敗已在修正後定向重跑通過；混合時間點的大跑也不能取代最終版本驗收。

另在 Pi 2 的隔離 smoke 準備階段，觀察到附註解的 fallback sequence 清空後產生無法解析的 YAML；桌面端已獨立重現（ruamel 0.18.16／0.18.17 都有），新增根層與巢狀 regression tests。修正將原有 guidance 移至 key 前並保留空 list；serializer 輸出也在 atomic replace 前重新解析，無效 YAML 或非 mapping 直接拒絕，不覆蓋原檔。負控已確認原檔保留。此修正已重新建置 wheel 並在 Pi 2 安裝重測通過。

遠端 `pi2-lite` 保護規則經只讀確認：兩個必要 check、strict up-to-date、1 位 reviewer 核准及 last-push approval，且管理員也受約束。不能自行核准自己的 PR、移除保護、偽造 check 或直接推送受保護分支。

## 本輪補充修正

- client session 的 PATH 維持使用者優先，Hermes CLI 仍作 fallback；sealed payload 的安全 launcher 順序不變。新負控先在乾淨上游證明 3 failed／2 passed，修正後含既有測試 109 passed／5 個他平台 skipped。
- 版本挑選器恢復 origin 為準及 tagless clone 支援，保留 fork 的可達性／tagger 日期規則，支援正式 SemVer／CalVer／IoT／Pi2，拒絕 RC、canary 與 backup；只發布所選 local tag，private refs 離開即清除。7 項實際 Git fixture 通過。
- 將 website dependency guard 移至 JS lane，改測安全 floor 與 exact-pin，不再凍結已更新的舊版號。
- provider discovery 測試隔離真實本機 Ollama/native catalog；first-run 無 executor 測試明確停用 free tier，並隔離主機 keyring-backed gh 認證。合計 20 項通過，未變更正式認證策略。

## 2026-11-01 候選與遠端 CI 補記

- 已建立並推送本機 merge commit `ec5b3254922ecf66b0374513b568a214fb0c756b`；另以 `593d3158d8` 將完整 Python CI 分成 8 個公開 runner 分片，未刪減測試，新增分片完整分割測試通過。草稿 PR：[#47](https://github.com/matttest0080-prog/hermes-agent-iot/pull/47)，**尚未遠端合併**。
- repository Actions 原先停用，現已啟用；workflow token 維持 read，禁止 workflow 核准 PR，分支保護未修改。已 dispatch 真實 CI 與 Pi2 install guards；後者通過，完整 CI 尚未全綠。後續提交須以 PR synchronize 事件取得真正 PR checks，不能將 dispatch 的成功當成已滿足全部 PR gates。
- 四個完整 JS 測試 lane 已完成：Desktop UI **11,512 passed**；Electron **3,681 passed、25 skipped**；tests-js **215 passed、1 skipped**；TUI **1,881 passed**。這是完整 lane 重跑，不再只引用局部測試；不等同最終遠端全部 CI 通過。
- 發現本機先前 `pm.build_env` 的測試環境誤裝 editable 專案，會讓復原 fixture 跨入原 checkout。改用與 CI `ensure_testenv` 一致的 `--no-install-project` 獨立環境後，復原 closure **14 passed**，未豁免或略過測試。
- 冷啟動 fixture 補齊真正 source-completion 所需的 agent／platform／根層 bootstrap helpers，以及 dotenv 依賴；保留舊 Python 3.11 啟動、切換 managed Python 3.14、原設定遷移及修復不覆寫的斷言。兩種 cold-runtime 情境通過。
- PTY 局部兩檔 **22 passed**，但 40 檔併跑仍出現兩項 PTY 失敗，因此不能宣稱已修復。曾試加的兩個 live-system-guard bypass marker 已撤回：沒有證據證明防護是原因，撤回後相同局部測試仍 22 passed。全域 live-system guard 自測 **47 passed**。附件路由測試的 driver lease 改為 5 秒，避免無關的 0.4 秒租約在忙碌 runner 先到期；保留拒絕附件與不提交 turn 的斷言。
- 真實 macOS CI 揭露 SQLite browse 的 `BEGIN IMMEDIATE` 中斷不在 rollback／逾時分類範圍。修正將 BEGIN 納入相同錯誤處理，清除 progress handler 後 rollback，僅在 deadline 已觸發時將 SQLite error 分類為 browse budget exceeded。新增 8 個 deterministic 正／負控制：乾淨上游 **3 failed、5 passed**，修正後 **8 passed**；無逾時的 SQLite error 保持原錯誤，並逐 byte 確認歷史／schema 回滾。既有 browse schema 檔 **29 passed**；仍須 macOS CI 重驗，不能把 Linux 測試稱為 macOS 實測。
- Pillow/browser-harness 阻擋仍在：最新 PyPI metadata 再查仍是 `browser-harness==0.1.13` 精確要求 Pillow 12.3.0，沒有以不相容 override 或 `--no-deps` 假裝修復。

### 最新實測與未過項目

- `2622c537af`：8 檔定向測試 **126 passed**；其後 40 檔重跑 **525 passed、4 failed、6 skipped**，PTY、update-lock 併發嘗試數及 delegation queue timeout 仍未過，不以單次局部綠燈豁免。hosted-room service 亦出現過 transient 失敗，最後重試通過不代表穩定性已證明。
- `2622c537af` 真實 PR CI 的 macOS 兩個分片均成功，已補足上段 SQLite 修正的 macOS 重驗；整體 CI 仍未通過。
- 同 commit 的新 wheel SHA256：`18536a8c7eb7ec16564c03151cf58632ae916cbcf96ff245cbc6062c1e1f3895`。Pi 2 隔離環境以一般 pip 重新安裝（未用 `--no-deps`），`pip check` 與 7 項 smoke 再通過；仍不代表 Pillow 缺口已解決。
- 完整 JS lane 先前本機使用 Node 22；遠端 PM 釘選 Node **26.12.1**，其 Storage fallback 是 own-method object，不是 jsdom prototype。修正 spy 選取真正 method owner，新增確實嘗試持久化的斷言；Node 26 的 voice/debounce 兩檔 **32 passed**，不是以 Node 22 的全量結果宣稱 Node 26 全量通過。
- 遠端 Python 第 2 分片揭露 DST 當天測試誤拿「現在」offset 比較「下次排程」offset，以及 no-sqlite fixture 未隔離 import-time unsafe CLI refusal。修正測試的參照時刻與真正讀取 seam，兩檔 **14 passed、4 個需 SQLite salvage shell 的既有 skipped**；未修改 cron 時區或 SQLite 安全政策。
- Nix PR CI **失敗**：offline npm install 對 zod 發出 registry request，遭 `ENOTCACHED`。尚未釐清 root override／workspace manifest 與 importNpmLock 改寫的相容性；未刪除 Nix check、開放 sandbox 網路或停用 14 日 age gate。
- 仍須完整最新 CI、Pillow 正式相容解法與獨立 reviewer；PR 維持草稿，沒有啟用 auto-merge 或繞過保護。

### 2026-11-01 後續：Nix closed-graph 安裝與 macOS deadline

- 先保留舊 CI 的 jobs／結論，再取消被取代且卡住的兩個 run（不是將它們改判成功）。其中 `2622c537af` 的 45 個已完成 jobs 都成功，但仍有一個 queued job；force-cancel 後，最新 `75cb1d0f77` 的完整 CI 才真正開始執行。
- Nix 已重現真正原因：importNpmLock 為避免 file: dependency 的 EOVERRIDE 而移除 root overrides，但原 workspace／transitive specs 與鎖定的 override 版本不一致，offline npm 因而要求 registry metadata。新增 `scripts/nix/freeze-npm-graph.mjs`，只在 hook 已保存原 manifest 的 disposable build tree 中將 dependency edges 表達成既有鎖圖版本；tarball resolved／integrity／version、peer constraints 不變，不解析新版本，安裝後還原 workspace 原檔。未停用 age gate、未開 sandbox 網路、未修改正式 npm manifests 或鎖定 artifact。
- 新增 3 個行為測試，含真實 npm 完全 offline 安裝：對照組移除 overrides 後必須 ENOTCACHED；修正組模擬 importNpmLock 的 file tarball 與 workspace-link 改寫，從無 node_modules 狀態安裝成功、執行實際模組、確認原 dependency package metadata 未改，並 byte-identical 還原 workspace。Node 26 完整 tests-js 為 **38 檔、218 passed、1 skipped**；CLI 最終定向 3 項通過。仍須真正 Nix CI 驗證，不能稱已完成 Nix 實測。
- 最新 macOS CI 另揭露 browse lease 超時：connection durability PRAGMAs 在 progress deadline 啟用之前執行，忙碌磁碟可能把 gateway 的 5 秒保留等待用盡。將連線設定也納入原有 budget／rollback 範圍，沒有放寬時限。擴充 configure／BEGIN／DDL 共 12 項正負控制；乾淨上游 **7 failed、5 passed**，修正後連既有 browse 檔 **41 passed**。等待新版 macOS CI 重驗。
- 重新查證公開 advisory **GHSA-8g5g-8vmr-9782**：Pillow <=12.3.0 為 critical JPEG heap-buffer overflow，first patched 13.0.0。不能把此問題降格為單純版號差異。browser-harness 的正式 0.1.x 發布 metadata 均固定 Pillow 12.2.0／12.3.0，最新 0.1.13 及其原始碼仍固定 12.3.0；目前沒有可直接換上的已修補正式 artifact。尚未發布第三方 fork、偽造 METADATA 或用 no-deps 規避；此項仍阻擋安全合併。
- reviewer 已在 `75cb1d0f77` 核准；後續 production code 提交仍須依 last-push approval 規則重新審查，不能沿用舊核准繞過保護。

## 繼續順序

1. 先以可回溯的本機 merge commit 固定候選，讓從 HEAD 建 fixture 的安裝／復原測試確實測到本次合併；收齊 Python／JS 結果並重跑受影響範圍。
2. 解決 Pillow/browser-harness 的正式安裝衝突；不得忽略 Pillow 12.3 的已知安全修補缺口。
3. 對最終索引快照重跑 lint、health、鎖檔及 Pi 2 必要驗證，完成差異審查。
4. 本機候選驗證後推送工作分支，以 PR 執行遠端完整 CI；在必要 check 全通過、相容性風險完成審查且另一位 reviewer 核准前，不合併受保護分支。

本機證據：系統暫存目錄下的 `hermes-v0225-evidence/`。未追蹤的 `owned/` 保留原樣，未打包、未提交。
