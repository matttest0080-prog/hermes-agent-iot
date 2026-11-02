# v0.22.5 安全依賴收斂與驗收界線

本文件記錄正式 `v0.22.5` 同步候選的依賴修補，**不代表 PR 已合併、已部署或已發布 PyPI**。Hermes 來源仍固定正式 tag，不改追 main。

## Python

Pillow／browser-harness 的來源、授權、固定 wheel 雜湊及 GitHub-only 交付限制見 [browser-harness-compat.md](browser-harness-compat.md)。不以忽略依賴、改寫既有第三方 wheel METADATA 或 `pip check` 成功冒充漏洞修復。

後續 OSV 掃描揭露的修補包含：brotlicffi 1.2.1.0、filelock 4.2.6、mem0ai 2.0.18、msgpack 1.2.4、OpenTelemetry 1.45.1 家族、pyasn1 0.6.5、setuptools 84.1.0、Tornado 6.6。

- 新增的 transitive 限制是 resolver 必須滿足的 **constraints**，不是忽略供應商相容界限的 overrides。filelock／msgpack／Tornado 固定已審核版本，避免套件級新鮮度例外放行未來版本。
- 舊 Mistral SDK 2.4.8 的 semantic-conventions 上限與修補後的 OpenTelemetry 不相容，因此改用正式 2.x SDK 2.10.1；沒有強制越過舊版 metadata。現有程式使用 `mistralai.client.Mistral`，實際新 SDK 匯入與 transcription API 建構已檢查。
- 全域仍是 **14 日**；僅逐套件、附理由的安全例外。沒有全域關閉 age gate。
- 根鎖供一般 managed runtime；Pi 2 鎖獨立解析 CPython 3.11–3.13／ARMv7。相容的既有 range pins 不因再生浮動，保留 interpreter markers；只更新有變更或違反安全限制的閉包。
- uv export 會移除直接 URL 的 hash fragment。產生器先核對 artifact URL 與既有匯出 digest，再恢復與 wheel Requires-Dist 完全相同的 URL，避免 pip 在 `--require-hashes` 模式將其當作另一個缺 hash 的 requirement。
- Pi 2 的 uvloop 排除同時反映於 wheel dependency marker 與 PM 明示請求的 refusal gate；不能只從鎖檔刪掉依賴而讓 `[full]` 安裝重新拉回。

## JavaScript：只透過 GitHub 交付的相容產物

公開通告尚無可用官方 deepmerge 修正版；直接以 minimatch 11 取代所有舊版，則會移除舊消費端需要的 `makeRe`／RegExp set。兩者均以獨立 repository 交付，不把第三方產品原始碼搬進 Hermes core。

| 產物 | 來源與修補 | 固定 SHA256 |
|---|---|---|
| `deepmerge@4.3.2-hermes.1` | 官方 v4.3.1 `5b87756a5671635679001cbac72aa42f23472c81`；來源及 target 複製迴圈均拒絕 `__proto__`，修補 GHSA-gcqx-w48m-w2h4 | `b5e9e519aef40cb14464bb1660856d5def5d30db2e7ce57c34f26f697578d9fd` |
| `@hermes-iot/minimatch-compat@10.2.7-hermes.1` | 官方 v10.2.6 `ded1bbd01beca62a5978bc1650ed0a1ccf9039d5`；回移官方 11.0.1 的 preprocessing bounds／大型集合 dedupe 保護，修補 GHSA-g3hv-75wg-m249，保留舊 API 並提供 callable CJS | `6c07658057a8cf4adbe457ae6af230fee705a5af6373475c2445e4337bc52b20` |

- [deepmerge 來源／release](https://github.com/matttest0080-prog/deepmerge-hermes-compat/releases/tag/v4.3.2-hermes.1)：候選來源 commit `a3bf1e278b9a1f01c9ebba32387dc7658bd8879c`，保留原作者及 MIT。
- [minimatch 來源／release](https://github.com/matttest0080-prog/minimatch-hermes-compat/releases/tag/v10.2.7-hermes.1)：候選來源 commit `695149e1c2340007c97e1ba4680481a4b9de9887`，保留原作者及 Blue Oak Model License 1.0.0。
- 兩者均非官方發行，`private: true` 禁止 npm registry 發布。套件名稱反映獨立維護責任；**不能只憑改名或掃描器沒有此 purl 的通告就宣稱安全**。依據是公開來源差異、修補前後控制及實際消費端驗證。
- Deepmerge CI `41369862063`：Node 22／26 × Linux／macOS／Windows 六組成功，各含 142 tape assertions、README 範例及 TypeScript 檢查。
- Minimatch CI `41370622593`：保留三個 Node 版本、四種 OS／shell 組合，共十二組成功；含原始 tap、新 API 與 CJS／ESM 型別驗證。本機 Linux 為 6,241 tap assertions、17 項 API 控制，均通過。
- 發布的是 CI artifact；在相同 checkout basename、Node 26／npm 12 下重建 byte-identical。舊 deepmerge Rollup 會將 checkout basename 編入私有變數名稱，**不是任意路徑皆 byte-identical**。

根與 website 的 GitHub tarballs 必須明示於 root dependencies，overrides 僅參照已審核來源；`package-lock.json` 記錄實際 SHA512 integrity。npm 12 設定維持 `allow-remote=root`，不允許任意 transitive remote。根／website 的普通 `npm ci` 已在此設定下安裝成功，未帶放寬參數。

鎖檔移轉時，npm 12 曾保留已無效的舊 minimatch preferences；只移除失效的生成紀錄，再交由 npm 從真實 artifact 再生，沒有手填版本或 integrity。解析階段的一次性 remote opt-in 不寫入交付設定，也沒有關閉 14 日政策。

其他修補包括 glob 14.0.2（僅取代 9+ 消費端）、官方 minimatch 11.0.1、Joi 17.13.9／18.3.1，以及 Photon／WhatsApp 獨立鎖的 undici、zod、body-parser、qs。glob 的新必要閉包採逐套件新鮮度例外並固定版本，不全域放行新套件。

## 目錄資料採獨立 PR

原上游准入規則禁止同一 PR 同時修改 catalog entries 與執行驗證的 tooling／core；這是安全設計，不為同步分支加入信任例外。

1. 核心同步 PR 暫保留 `pi2-lite` 原有 YAML entries，README／驗證工具可先同步；舊 614 個檔案已通過新版 structural validator。
2. 正式 v0.22.5 entries 差異另存為 data-only patch，於獨立 PR 完成來源 pin 驗證與受保護合併。
3. Pinned-source gate 改為八個分片；真實 shell／git fixture 驗證所有 entries 恰好各處理一次，無效 shard 不得假綠，既有 confinement／供應鏈負控保留。

**兩部分皆合併才算整次同步完成。**

## 驗收範圍

獨立套件 CI 不等於 Hermes 全量 CI；工作樹或舊 head 的局部結果不能代替最終提交。最後仍需完整 required checks、最新提交的獨立 approval、Pi 2 installed-wheel 與五 profiles 的一般 pip／hash 驗證。

localhost fixture、dry-run、resolver 成功與 `pip check` 不是真實模型、MQTT、Home Assistant、電話服務或長期負載驗收；也未宣稱 catalog 內所有第三方外掛的各自依賴均已完成漏洞審核。
