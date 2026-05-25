import {
  tableTitleStyle,
  tableWrapStyle,
  tableStyle,
  thStyle,
  tdStyle,
  emptyTdStyle,
  trStyle,
} from "../styles";

export function SimpleTable({
  title,
  headers,
  rows,
}: {
  title?: string;
  headers: string[];
  rows: Array<Array<string | number | null | undefined>>;
}) {
  return (
    <div style={{ marginTop: 14 }}>
      {title && <div style={tableTitleStyle}>{title}</div>}

      <div style={tableWrapStyle}>
        <table style={tableStyle}>
          <thead>
            <tr>
              {headers.map((header) => (
                <th key={header} style={thStyle}>
                  {header}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td style={emptyTdStyle} colSpan={headers.length}>
                  目前沒有資料
                </td>
              </tr>
            ) : (
              rows.map((row, rowIndex) => (
                <tr key={rowIndex} style={trStyle}>
                  {row.map((cell, cellIndex) => (
                    <td key={`${rowIndex}-${cellIndex}`} style={tdStyle}>
                      {cell ?? "-"}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
