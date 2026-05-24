import type { CurrentUser, Sample, Transfer } from '../types'
import { StatusBadge } from './StatusBadge'
import {
  emptyStyle,
  monoTdStyle,
  primaryButtonStyle,
  readonlyHintStyle,
  tableStyle,
  tdStyle,
  thStyle,
} from '../styles'
import {
  getDisplaySampleLocation,
  getDisplaySampleStatus,
  isFactoryUser as checkIsFactoryUser,
  isSampleInCurrentLab,
} from '../utils/sampleDisplay'

type SampleTableProps = {
  loading: boolean
  samples: Sample[]
  selectedSampleId: string | null
  detailOpen: boolean
  currentUser: CurrentUser
  outgoingTransfersBySampleId: Map<string, Transfer>
  onOpenDetail: (sampleId: string) => void
}

export function SampleTable({
  loading,
  samples,
  selectedSampleId,
  detailOpen,
  currentUser,
  outgoingTransfersBySampleId,
  onOpenDetail,
}: SampleTableProps) {
  const isFactoryUser = checkIsFactoryUser(currentUser)

  if (loading) {
    return <div style={emptyStyle}>載入中...</div>
  }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={tableStyle}>
        <thead>
          <tr style={{ background: 'var(--s2)' }}>
            {[
              '樣品編號',
              '委託單號',
              '樣品名稱',
              '實驗需求',
              '狀態',
              '目前位置',
              '操作',
            ].map((header) => (
              <th key={header} style={thStyle}>
                {header}
              </th>
            ))}
          </tr>
        </thead>

        <tbody>
          {samples.map((sample) => {
            const active = sample.id === selectedSampleId && detailOpen
            const canCurrentUserOperateThisSample = isSampleInCurrentLab(sample, currentUser)
            const outgoingTransfer = outgoingTransfersBySampleId.get(sample.id)
            const displayStatus = getDisplaySampleStatus(sample, currentUser, outgoingTransfer)
            const displayLocation = getDisplaySampleLocation(sample, currentUser, outgoingTransfer)

            return (
              <tr
                key={sample.id}
                style={{
                  borderBottom: '1px solid rgba(56,139,253,0.08)',
                  background: active ? 'rgba(56,139,253,0.08)' : 'transparent',
                }}
              >
                <td style={monoTdStyle}>{sample.sample_no}</td>
                <td style={monoTdStyle}>{sample.order_no}</td>
                <td style={tdStyle}>{sample.sample_name ?? '-'}</td>
                <td style={tdStyle}>{sample.experiment_item ?? '-'}</td>
                <td style={tdStyle}>
                  <StatusBadge status={displayStatus} />
                </td>
                <td style={tdStyle}>
                  <div>{displayLocation}</div>
                  {!isFactoryUser && !canCurrentUserOperateThisSample && (
                    <div style={readonlyHintStyle}>歷史紀錄 / 只可查看</div>
                  )}
                </td>
                <td style={tdStyle}>
                  <button onClick={() => onOpenDetail(sample.id)} style={primaryButtonStyle}>
                    查看
                  </button>
                </td>
              </tr>
            )
          })}

          {samples.length === 0 && (
            <tr>
              <td colSpan={7} style={emptyStyle}>
                目前沒有樣品資料
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
