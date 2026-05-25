export function ConfigBanner({ message, type = "warn" }: { message: string; type?: "warn" | "error" | "info" }) {
  const colors = {
    warn: "border-hive-warn/50 bg-hive-warn/10 text-amber-200",
    error: "border-hive-danger/50 bg-hive-danger/10 text-red-200",
    info: "border-hive-accent/50 bg-hive-accent/10 text-blue-200",
  };
  return (
    <div className={`mb-4 px-4 py-3 rounded-lg border text-sm ${colors[type]}`}>
      {message}
    </div>
  );
}
