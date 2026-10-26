/**
 * Format timestamp into relative display string for last sync indicators.
 */
export function formatLastSynced(date) {
  if (!date) return 'Never';
  const timestamp = typeof date === 'string' || typeof date === 'number'
    ? new Date(date).getTime()
    : (date instanceof Date ? date.getTime() : NaN);

  if (isNaN(timestamp)) return 'Never';

  const diffSec = Math.max(0, Math.floor((Date.now() - timestamp) / 1000));
  if (diffSec < 10) return 'Just now';
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour}h ago`;
  return new Date(timestamp).toLocaleDateString([], { month: 'short', day: 'numeric' });
}
