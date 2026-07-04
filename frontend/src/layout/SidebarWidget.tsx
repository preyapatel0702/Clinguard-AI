export default function SidebarWidget() {
  return (
    <div
      className={`
        mx-auto mb-10 w-full max-w-60 rounded-2xl bg-gray-50 px-4 py-5 text-center dark:bg-white/[0.03]`}
    >
      <h3 className="mb-2 font-semibold text-gray-900 dark:text-white">
        System Status
      </h3>
      <p className="mb-1 text-gray-500 text-theme-sm dark:text-gray-400">
        All monitored models reporting
      </p>
      <div className="mx-auto mt-3 flex items-center justify-center gap-1.5">
        <span className="h-2 w-2 rounded-full bg-success-500" />
        <span className="text-theme-xs font-medium text-success-600 dark:text-success-500">
          Operational
        </span>
      </div>
    </div>
  );
}
