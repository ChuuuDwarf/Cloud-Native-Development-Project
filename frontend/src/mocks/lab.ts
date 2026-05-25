// 後端離線時的固定展示假資料（fallback）。
// 對應後端初始種子，方便 demo 不依賴後端啟動。
// 注意：fallback 模式下操作不會真正改變狀態，頁面會提示「離線展示資料」。
// （由原 frontend/lib/mock.ts 搬遷至 src/mocks/，對齊 README 結構。）

import type { ClosureCheck, Report, StorageItem, Wip } from "@/types/lab";

export const MOCK_WIPS: Wip[] = [
  { wipId: 'WIP-0891-01', orderId: 'WO-2024-0891', sample: '晶圓#A-1', experimentItem: 'IC電性', machineId: 'TEM-001', recipe: 'RCP-TEM-v2.3', status: '執行中', progress: 72, operator: '陳明德', checkInAt: '2026-05-21 09:00:00', checkOutAt: null, resultNote: null, rawDataUrl: null, dataVerified: false, abort: null, history: [{ time: '2026-05-21 09:00:00', action: '上機', by: '陳明德', note: '機台 TEM-001 / RCP-TEM-v2.3' }] },
  { wipId: 'WIP-0891-02', orderId: 'WO-2024-0891', sample: '晶圓#A-2', experimentItem: '電阻量測', machineId: 'XRD-002', recipe: 'RCP-XRD-v1.5', status: '執行中', progress: 45, operator: '陳明德', checkInAt: '2026-05-21 09:00:00', checkOutAt: null, resultNote: null, rawDataUrl: null, dataVerified: false, abort: null, history: [] },
  { wipId: 'WIP-0895-01', orderId: 'WO-2024-0895', sample: '金屬片', experimentItem: 'SEM分析', machineId: 'SEM-001', recipe: 'RCP-SEM-v3.1', status: '已下機', progress: 60, operator: '林佳慧', checkInAt: '2026-05-21 09:00:00', checkOutAt: null, resultNote: '影像偏移，疑似載台異常', rawDataUrl: null, dataVerified: false, abort: { reason: 'SEM 影像數據異常，需人工判定', by: '林佳慧', status: '待主管判定', requestedAt: '2026-05-21 11:00:00' }, history: [] },
  { wipId: 'WIP-0894-01', orderId: 'WO-2024-0894', sample: '銅導線框架', experimentItem: '熱阻分析', machineId: 'THR-001', recipe: 'RCP-THR-v1.0', status: '待確認', progress: 100, operator: '張建平', checkInAt: '2026-05-21 09:00:00', checkOutAt: '2026-05-21 11:30:00', resultNote: '熱阻量測完成，數值在規格內', rawDataUrl: '/data/WIP-0894-01.csv', dataVerified: true, abort: null, history: [] },
  { wipId: 'WIP-0896-01', orderId: 'WO-2024-0896', sample: '玻璃基板', experimentItem: 'X-Ray', machineId: 'XRD-002', recipe: 'RCP-XRD-v1.5', status: '已完成', progress: 100, operator: '張建平', checkInAt: '2026-05-20 14:00:00', checkOutAt: '2026-05-20 16:00:00', resultNote: 'X-Ray 影像清晰，無異常', rawDataUrl: null, dataVerified: true, abort: null, history: [] },
  { wipId: 'WIP-0892-01', orderId: 'WO-2024-0892', sample: '玻璃基板', experimentItem: '光學量測', machineId: 'OPT-001', recipe: 'RCP-OPT-v2.0', status: '待上機', progress: 0, operator: null, checkInAt: null, checkOutAt: null, resultNote: null, rawDataUrl: null, dataVerified: false, abort: null, history: [] },
];

export const MOCK_REPORTS: Report[] = [
  { reportId: 'RPT-0896-01', orderId: 'WO-2024-0896', wipId: 'WIP-0896-01', title: 'WO-2024-0896 X-Ray 檢查報告', summary: '對玻璃基板進行 X-Ray 檢查。', conclusion: '未發現裂痕或異物，判定合格。', attachments: [], status: '已回傳', createdAt: '2026-05-20 16:30:00', createdBy: '張建平', versions: [{ version: 1, status: '已回傳', at: '2026-05-20 16:30:00', by: '張建平', note: '初版' }] },
  { reportId: 'RPT-0893-01', orderId: 'WO-2024-0893', wipId: 'WIP-0893-01', title: 'WO-2024-0893 化學分析報告', summary: '化學成份分析。', conclusion: '成份比例符合需求。', attachments: [], status: '已回傳', createdAt: '2026-05-19 10:00:00', createdBy: '張建平', versions: [{ version: 1, status: '已回傳', at: '2026-05-19 10:00:00', by: '張建平', note: '初版' }] },
];

export const MOCK_CLOSURES: ClosureCheck[] = [
  { orderId: 'WO-2024-0896', status: '待取件', canClose: true, conditions: [{ name: '所有實驗明細完成或終止', ok: true }, { name: '所有 WIP 已結束', ok: true }, { name: '數據已收集', ok: true }, { name: '無未結異常', ok: true }, { name: '樣品已入庫或待返還', ok: true }, { name: '報告已建立或已回傳', ok: true }] },
  { orderId: 'WO-2024-0894', status: '待結果確認', canClose: false, conditions: [{ name: '所有實驗明細完成或終止', ok: false }, { name: '所有 WIP 已結束', ok: false }, { name: '數據已收集', ok: true }, { name: '無未結異常', ok: true }, { name: '樣品已入庫或待返還', ok: false }, { name: '報告已建立或已回傳', ok: false }] },
  { orderId: 'WO-2024-0893', status: '已結案', canClose: true, conditions: [{ name: '所有實驗明細完成或終止', ok: true }, { name: '所有 WIP 已結束', ok: true }, { name: '數據已收集', ok: true }, { name: '無未結異常', ok: true }, { name: '樣品已入庫或待返還', ok: true }, { name: '報告已建立或已回傳', ok: true }] },
];

export const MOCK_STORAGE: StorageItem[] = [
  { storageId: 'ST-2024-0896', orderId: 'WO-2024-0896', sample: '玻璃基板', qty: '10片', status: '待返還', location: 'A-03-12', history: [{ time: '2026-05-20 16:00:00', action: '建立倉儲紀錄', by: '系統', note: '' }] },
  { storageId: 'ST-2024-0895', orderId: 'WO-2024-0895', sample: '金屬片', qty: '10片', status: '已入庫', location: 'B-01-05', history: [{ time: '2026-05-21 10:30:00', action: '建立倉儲紀錄', by: '系統', note: '' }] },
  { storageId: 'ST-2024-0893', orderId: 'WO-2024-0893', sample: '化學試片', qty: '5片', status: '已取件', location: '—', history: [{ time: '2026-05-19 09:00:00', action: '建立倉儲紀錄', by: '系統', note: '' }] },
];
