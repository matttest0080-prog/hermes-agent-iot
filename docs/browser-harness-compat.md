# browser-harness／Pillow 13 相容性產物

## 原因與交付限制

公開 critical advisory `GHSA-8g5g-8vmr-9782` 影響 Pillow <=12.3.0，首個修補版為 13.0.0。browser-harness 官方 0.1.13 精確要求 Pillow 12.3.0，不能靠 uv override、`--no-deps`、偽造 METADATA 或忽略 `pip check` 解決正式相依衝突。

本候選依使用者延續指示採用獨立相容性 fork 的固定 GitHub artifact，**暫不發布此 Hermes 候選至 PyPI**。根專案原有 `sanitize_release_wheel.py` 保持 fail-closed：它會拒絕這個新的 core direct URL，阻止原 PyPI publisher 繼續。GitHub／隔離驗證用的 Hermes wheel 應保留原始 PEP 508 metadata，不執行 PyPI sanitizer；沒有刪除 browser-harness dependency 或偽裝成官方新版。

## 固定來源與可重現產物

- 原始官方來源：`browser-use/browser-harness`，`v0.1.13`，commit `c24e5072ee66f8499bacd663f4f4bcb089bc4492`。
- 獨立 fork：https://github.com/matttest0080-prog/browser-harness-hermes-compat
- fork tag：`v0.1.13.post1`；commit `f387133ecc9561128d18eabc4af6df143b2560d5`。
- 發行：https://github.com/matttest0080-prog/browser-harness-hermes-compat/releases/tag/v0.1.13.post1
- wheel：`browser_harness-0.1.13.post1-py3-none-any.whl`
- wheel SHA256：`63a2fb36e398d8a764fb5961a70f0deb63dc60472ff0345b739105d17e2e059e`
- sdist SHA256：`fe7e998093aab5aee0e290290f380eff386eaa617883174cede325b63b6f7b43`
- CI receipt：https://github.com/matttest0080-prog/browser-harness-hermes-compat/actions/runs/41299446511

消費端在 project dependency、uv.lock 與 Pi2 hashed locks 固定 URL／SHA256，不追蹤浮動 branch。GitHub asset 的 SHA256SUMS 與 CI 下載產物一致。每次重建應使用已固定 source commit 與 SOURCE_DATE_EPOCH，不能直接替換同 tag 的產物。

## 審查範圍

fork 保留 Browser Use 原始 MIT License（Copyright 2026 Browser Use）、README、技能識別與全部 `src/`；`git diff v0.1.13 -- src` 為空。變更為正式套件版本 `0.1.13.post1`、Pillow 13.0.0、可選 MCP 2.3.0、正確 fork URL、來源說明、CI 與相容性測試。原 PyPI publisher 已改成只讀驗證，不向 PyPI 發布此第三方 fork。

- Python 3.11、3.12、3.13、3.14 的真實 CI 各自 **257 tests passed**，含全部上游單元測試及新增 JPEG 解碼、contact sheet、遮罩、無效影像拒絕控制。
- 使用實際 wheel 安裝，不以 editable source 冒充 wheel；`pip check` 與 metadata／實際 import 路徑檢查通過。
- 每個 CI matrix 以同 epoch 建 wheel 兩次，逐 byte 比對一致。
- 此新 post-release 使用原有 browser-harness 的逐套件 age-gate 例外，理由為已審查的 critical 修補相容性；沒有關閉 14 日政策。
- **不是**真實 Chrome／Browser Use Cloud、模型品質、全部作業系統或長期負載驗證。Hermes 與 Pi2 的整合驗證另列於 `upstream-review-v0.22.5.md`。

官方後續若發布與安全 Pillow 相容的正式 artifact，應重新審查並移除不必要的 fork；不得默默將 URL 改回仍綁定脆弱 Pillow 的版本。
