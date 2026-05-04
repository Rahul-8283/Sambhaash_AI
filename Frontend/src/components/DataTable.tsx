/**
 * Reusable data table component
 */

import React, { useState } from "react";
import { ChevronUp, ChevronDown } from "lucide-react";
import clsx from "clsx";

interface Column<T> {
  key: keyof T;
  label: string;
  sortable?: boolean;
  render?: (value: unknown, row: T) => React.ReactNode;
  width?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  rowKey: keyof T;
  onRowClick?: (row: T) => void;
  selectable?: boolean;
  onSelectionChange?: (selectedRows: T[]) => void;
}

export const DataTable = React.forwardRef<
  HTMLTableElement,
  DataTableProps<any>
>(({
  columns,
  data,
  rowKey,
  onRowClick,
  selectable = false,
  onSelectionChange,
}, ref) => {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
  const [selectedRows, setSelectedRows] = useState<Set<any>>(new Set());

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDirection("asc");
    }
  };

  const handleSelectRow = (row: any) => {
    const newSelected = new Set(selectedRows);
    if (newSelected.has(row[rowKey])) {
      newSelected.delete(row[rowKey]);
    } else {
      newSelected.add(row[rowKey]);
    }
    setSelectedRows(newSelected);
    if (onSelectionChange) {
      onSelectionChange(data.filter((r) => newSelected.has(r[rowKey])));
    }
  };

  const handleSelectAll = () => {
    if (selectedRows.size === data.length) {
      setSelectedRows(new Set());
      if (onSelectionChange) onSelectionChange([]);
    } else {
      const newSelected = new Set(data.map((r) => r[rowKey]));
      setSelectedRows(newSelected);
      if (onSelectionChange) onSelectionChange(data);
    }
  };

  let sortedData = [...data];
  if (sortKey) {
    sortedData.sort((a, b) => {
      const aVal = a[sortKey as keyof typeof a];
      const bVal = b[sortKey as keyof typeof b];
      if (aVal < bVal) return sortDirection === "asc" ? -1 : 1;
      if (aVal > bVal) return sortDirection === "asc" ? 1 : -1;
      return 0;
    });
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table
        ref={ref}
        className="w-full text-sm text-gray-900 border-collapse"
      >
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr>
            {selectable && (
              <th className="px-6 py-3 text-left">
                <input
                  type="checkbox"
                  checked={selectedRows.size === data.length && data.length > 0}
                  onChange={handleSelectAll}
                  className="w-4 h-4 rounded border-gray-300"
                />
              </th>
            )}
            {columns.map((column) => (
              <th
                key={String(column.key)}
                className={clsx(
                  "px-6 py-3 text-left font-semibold text-gray-700",
                  column.sortable && "cursor-pointer hover:bg-gray-100"
                )}
                style={column.width ? { width: column.width } : undefined}
                onClick={() => column.sortable && handleSort(String(column.key))}
              >
                <div className="flex items-center gap-2">
                  {column.label}
                  {column.sortable && sortKey === String(column.key) && (
                    sortDirection === "asc" ? (
                      <ChevronUp size={16} />
                    ) : (
                      <ChevronDown size={16} />
                    )
                  )}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td
                colSpan={selectable ? columns.length + 1 : columns.length}
                className="px-6 py-8 text-center text-gray-500"
              >
                No data available
              </td>
            </tr>
          ) : (
            sortedData.map((row, idx) => (
              <tr
                key={String(row[rowKey])}
                className={clsx(
                  "border-b border-gray-200 hover:bg-gray-50 transition-colors",
                  onRowClick && "cursor-pointer",
                  idx % 2 === 0 && "bg-white"
                )}
              >
                {selectable && (
                  <td className="px-6 py-3">
                    <input
                      type="checkbox"
                      checked={selectedRows.has(row[rowKey])}
                      onChange={() => handleSelectRow(row)}
                      className="w-4 h-4 rounded border-gray-300"
                    />
                  </td>
                )}
                {columns.map((column) => (
                  <td
                    key={String(column.key)}
                    className="px-6 py-3"
                    style={column.width ? { width: column.width } : undefined}
                    onClick={() => onRowClick?.(row)}
                  >
                    {column.render
                      ? column.render(row[column.key], row)
                      : String(row[column.key])}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
});

DataTable.displayName = "DataTable";

export default DataTable;
